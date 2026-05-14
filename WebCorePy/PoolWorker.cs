using ClosedXML.Excel;
using Microsoft.Extensions.Logging;
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Text.Json.Nodes;
using System.Threading;
using System.Threading.Tasks;
using System.Threading.Tasks.Dataflow;

namespace WebCorePy
{
    public enum WorkerCommand
    {
        CHECK,
        START,
        STOP,
        CLEAR
    }

    public enum WorkerResult
    {
        SUCCESS,
        ERROR
    }

    public enum WorkerState
    {
        EMPTY,
        BUSY,
        READY
    }

    public struct WorkerRequest
    {
        public WorkerCommand command {  get; set; }
        public string train {  get; set; }
        public string predict { get; set; }
        public List<string> algorithms { get; set; }
        public int timeout { get; set; }
        public int folds { get; set; }

        public WorkerRequest(WorkerCommand command)
        {
            this.command = command;
            this.train = null;
            this.predict = null;
            this.algorithms = null;
            this.timeout = 0;
            this.folds = 0 ;
        }

        public WorkerRequest(WorkerCommand command, string train, string predict, List<string> algorithms, int timeout, int folds)
        {
            this.command = command;
            this.train = train;
            this.predict = predict;
            this.algorithms = algorithms;
            this.timeout = timeout;
            this.folds = folds;
        }
    }

    public struct WorkerResponse
    {
        public int id;
        public WorkerResult result;
        public WorkerState state;

        public decimal progress;
        public string[] output;

        public WorkerResponse(WorkerResult result, WorkerState state, decimal progress, string[] output)
        {
            this.result = result;
            this.state = state;

            this.progress = progress;
            this.output = output;
        }
    }

    public class PoolWorker
    {
        private Task _task;
        private CancellationToken ct;
        private int slot;
        private BufferBlock<WorkerRequest> _request_buffer;
        private BufferBlock<WorkerResponse> _response_buffer;

        private int _request_id;

        Process process;
        public WorkerState state;
        public DateTime? start;
        public DateTime? end;
        public string file_train;
        public string file_test;

        private List<string> messages = new List<string>();
        private WorkerRequest parameters;
        private decimal progress;
        private decimal step;
        private int currentAlgorithm;
        private bool cancel;

        private XLWorkbook workbook = null;
        private IXLWorksheet worksheet;

        private ILogger logger;

        public PoolWorker(CancellationToken ct, int slot, ILogger logger)
        {
            this.ct = ct;
            this.slot = slot;
            this.logger = logger;
            
            _request_buffer = new BufferBlock<WorkerRequest>();
            _response_buffer = new BufferBlock<WorkerResponse>();
            _task = Task.Run(() => Process(ct), ct);
            _request_id = 0; // TODO: do we need independent message count in workers? Remove if not.

            process = null;
            start = null;
            end = null;
            file_train = null;
            file_test = null;
        }

        private string decorateLogMessage(string message)
        {
            return $"SLOT {slot}: {message}";
        }

        public WorkerState State
        {
            get 
            {
                if (end != null)
                {
                    return WorkerState.READY;
                }
                else
                {
                    if (start == null)
                    {
                        return WorkerState.EMPTY;
                    }
                    else 
                    {
                        return WorkerState.BUSY;
                    }
                }
            }
        }

        public async Task<WorkerResponse> Command(WorkerRequest request)
        {
            _request_buffer.Post(request);
            WorkerResponse response = await _response_buffer.ReceiveAsync();
            return response;
        }

        private WorkerResult startAlgorithm(string algorithm, int folds, string train, string predict)
        {
            logger.LogInformation(decorateLogMessage(
                $"Starting algorithm {algorithm} with {folds} folds on '{train}' and '{predict}' datasets"
            ));

            ProcessStartInfo info = new ProcessStartInfo
            {
                UseShellExecute = false,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                CreateNoWindow = true,
                FileName = "py",
            };
            info.ArgumentList.Add("-3");
            info.ArgumentList.Add("py/evaluator.py");
            info.ArgumentList.Add("-a");
            info.ArgumentList.Add(algorithm);
            info.ArgumentList.Add("-e");
            info.ArgumentList.Add(folds.ToString());
            info.ArgumentList.Add("-t");
            info.ArgumentList.Add(train);
            if (predict != null)
            {
                info.ArgumentList.Add("-p");
                info.ArgumentList.Add(predict);
            }

            // outside processor should deal with data integrity
            process = new Process();
            process.StartInfo = info;
            process.OutputDataReceived += OutputDataReceived;
            process.ErrorDataReceived += ErrorDataReceived;
            process.EnableRaisingEvents = true;
            process.Exited += ProcessExited;

            var res = process.Start();
            process.BeginOutputReadLine();
            process.BeginErrorReadLine();

            return res ? WorkerResult.SUCCESS : WorkerResult.ERROR;
        }

        public WorkerResult Start(WorkerRequest request)
        {
            cancel = false;
            parameters = request;
            var numAlgorithms = parameters.algorithms.Count;
            
            if ((numAlgorithms > 0) && (request.train != null))
            {
                workbook = new XLWorkbook();
                worksheet = workbook.Worksheets.Add("training");
                worksheet.Cell(1, 1).InsertData(new[] { "", "Folds", "Method", "R2", "MAE", "MSE", "Time", "Status" }, transpose: true);

                messages = new List<string>();
                progress = 0;
                step =  (decimal)1.0 / numAlgorithms;
                currentAlgorithm = 0;

                start = DateTime.Now;
                end = null;

                return startAlgorithm(parameters.algorithms[currentAlgorithm], parameters.folds, parameters.train, parameters.predict);
            }
            else
            { 
                return WorkerResult.ERROR; 
            }
        }

        private void OutputDataReceived(object sender, DataReceivedEventArgs line)
        {
            logger.LogDebug(decorateLogMessage( // TODO: log buffer overflows when writing, use different library
                $"- {line.Data}"
            ));
            lock (messages)
            {
                messages.Add(line.Data);
            }
        }

        private void ErrorDataReceived(object sender, DataReceivedEventArgs line)
        {
            try
            {
                if (line.Data == null)
                {
                    return;
                }
                JsonNode data = (JsonObject)JsonNode.Parse(line.Data);
                var type = data["type"].ToString();
                switch (type)
                {
                    case "progress":
                        progress = (currentAlgorithm + (decimal)data["progress"]) * step;
                        logger.LogDebug(decorateLogMessage(
                            $"progress received: {progress}"
                        ));
                        break;
                    case "results":
                        logger.LogInformation(decorateLogMessage(
                            $"results received: {data.ToString()}"
                        ));
                        worksheet.Cell(currentAlgorithm + 2, 1).InsertData(new List<object> { 
                            currentAlgorithm + 1, 
                            (int)data["folds"], 
                            (string)data["method"],
                            data["r2"] != null ? (float)data["r2"]: null,
                            data["mae"] != null ? (float)data["mae"]: null,
                            data["mse"] != null ? (float)data["mse"]: null, 
                            (float)data["time"], 
                            (string)data["status"]
                        }, transpose: true);
                        break;
                    default:
                        logger.LogWarning(decorateLogMessage(
                            $"Unknown message type {type}"
                        ));

                        lock (messages)
                        {
                            messages.Add($"WARNING! unknown message type {type}");
                        }
                        break;
                }
            }
            catch (Exception ex)
            {
                lock (messages) 
                {
                    messages.Add(ex.Message);
                }
            }
        }

        private void ProcessExited(object sender, EventArgs e)
        {
            process.CancelOutputRead();
            process.CancelErrorRead();
            process.Dispose();
            process = null;

            start = DateTime.Now;
            currentAlgorithm++;
            progress = currentAlgorithm * step;

            if (cancel)
            {
                finished(false);
            }
            else
            {
                if (currentAlgorithm >= parameters.algorithms.Count)
                {
                    finished(true);
                }
                else
                {
                    startAlgorithm(parameters.algorithms[currentAlgorithm], parameters.folds, parameters.train, parameters.predict);
                }
            }
        }

        public void Stop()
        {
            cancel = true;
            if (process != null)
            {
                process.Kill();
            }
        }

        private void finished(bool success)
        {
            if (success)
            {
                workbook.SaveAs(Path.Combine(Directory.GetCurrentDirectory(), $"Data{slot + 1}", "report.xlsx"), true);
            }

            if (workbook != null)
            {
                workbook.Dispose();
                workbook = null;
            }

            start = null;
            end = success ? DateTime.Now : null;
        }

        public WorkerResult Restart(WorkerRequest request)
        {
            Stop();
            return Start(request);
        }

        private async void Process(CancellationToken ct) 
        {
            WorkerRequest request;

            logger.LogInformation(decorateLogMessage(
                $"Worker started"
            ));

            while (!ct.IsCancellationRequested)
            {
                if (_request_buffer.TryReceive<WorkerRequest>(out request))
                {
                    logger.LogInformation(decorateLogMessage(
                        $"Processing request {request.command}"    
                    )); 
                    
                    WorkerResult result = WorkerResult.SUCCESS;
                    switch (request.command)
                    {
                        case WorkerCommand.CHECK:
                            {
                                // do nothing
                                break;
                            }
                        case WorkerCommand.START:
                            {
                                result = Restart(request);
                                break;
                            }
                        case WorkerCommand.STOP:
                            {
                                Stop();
                                break;
                            }
                        case WorkerCommand.CLEAR:
                            {
                                // TODO: is it needed here?
                                break;
                            }
                    }

                    WorkerResponse response;
                    lock (messages)
                    {
                        response = new WorkerResponse(result, State, progress, messages.ToArray());
                        messages.Clear();
                    }

                    _response_buffer.Post<WorkerResponse>(response);
                }
                else
                {
                    await Task.Delay(10);
                }

                if (start != null)
                {
                    var elapsed = DateTime.Now - (DateTime)start;
                    if ((parameters.timeout > 0 ) && (elapsed.TotalSeconds > parameters.timeout))
                    {
                        logger.LogInformation(decorateLogMessage(
                            $"Processing stopped after {elapsed.TotalSeconds} seconds"
                        ));

                        var algorithm = (JsonObject)JsonNode.Parse(parameters.algorithms[currentAlgorithm]);
                        worksheet.Cell(currentAlgorithm + 2, 1).InsertData(new List<object> {
                            currentAlgorithm + 1, parameters.folds, (string)algorithm["name"],
                            null, null, null, elapsed.TotalSeconds, "timeout"
                        }, transpose: true);
                        process.Kill();

                        lock (messages)
                        {
                            messages.Add($"! Timed out and killed after {elapsed.TotalSeconds:F0} s");
                        }
                    }
                }
            }

            if (ct.IsCancellationRequested && (process != null))
            {
                process.Kill();
            }
            logger.LogInformation(decorateLogMessage(
                $"Worker stopped"
            ));
        }
    }
}
