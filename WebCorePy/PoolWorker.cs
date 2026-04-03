using ClosedXML.Excel;
using DocumentFormat.OpenXml.Office2016.Excel;
using Microsoft.EntityFrameworkCore.Metadata.Internal;
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
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
        public bool train {  get; set; }
        public bool test { get; set; }
        public List<string> algorithms { get; set; }
        public int timeout { get; set; }
        public int folds { get; set; }

        public WorkerRequest(WorkerCommand command)
        {
            this.command = command;
            this.train = false;
            this.test = false ;
            this.algorithms = null;
            this.timeout = 0;
            this.folds = 0 ;
        }

        public WorkerRequest(WorkerCommand command, bool train, bool test, List<string> algorithms, int timeout, int folds)
        {
            this.command = command;
            this.train = train;
            this.test = test;
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

        private XLWorkbook workbook = null;
        private IXLWorksheet worksheet;

        public PoolWorker(CancellationToken ct, int slot)
        {
            this.ct = ct;
            this.slot = slot;
            
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

        private WorkerResult startAlgorithm(string algorithm, int folds)
        {
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
            info.ArgumentList.Add("-f");
            info.ArgumentList.Add(folds.ToString());

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
            parameters = request;
            var numAlgorithms = parameters.algorithms.Count;
            
            if (numAlgorithms > 0)
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

                return startAlgorithm(parameters.algorithms[currentAlgorithm], parameters.folds);
            }
            else
            { 
                return WorkerResult.ERROR; 
            }
        }

        private void OutputDataReceived(object sender, DataReceivedEventArgs line)
        {
            lock (messages)
            {
                messages.Add(line.Data);
            }
        }

        private void ErrorDataReceived(object sender, DataReceivedEventArgs line)
        {
            lock (messages)
            {
                decimal current;
                var test = Decimal.TryParse(line.Data, CultureInfo.InvariantCulture, out current);
                progress = (currentAlgorithm + current) * step;
            }
        }

        private void ProcessExited(object sender, EventArgs e)
        {
            process.CancelOutputRead();
            process.CancelErrorRead();
            process.Dispose();
            process = null;

            // TODO: get data from the process and limiter
            worksheet.Cell(currentAlgorithm + 2, 7).Value = (DateTime.Now - (DateTime)start).TotalSeconds;
            worksheet.Cell(currentAlgorithm + 2, 1).Value = currentAlgorithm + 1;
            worksheet.Cell(currentAlgorithm + 2, 3).Value = "todo:";
            start = DateTime.Now;

            currentAlgorithm++;            
            if (currentAlgorithm >= parameters.algorithms.Count)
            {
                // TODO: full training and forecasting if needed
                finished(true);
            }
            else 
            {
                startAlgorithm(parameters.algorithms[currentAlgorithm], parameters.folds);
            }
        }

        public void Stop()
        {
            if (process != null)
            {
                currentAlgorithm = parameters.algorithms.Count;
                process.Kill();

                finished(false);
            }
        }

        private void finished(bool success)
        {
            workbook.SaveAs(Path.Combine(Directory.GetCurrentDirectory(), "wwwroot", $"trainging_{slot + 1}.xlsx"), true);
            workbook.Dispose();

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

            while (!ct.IsCancellationRequested)
            {
                if (_request_buffer.TryReceive<WorkerRequest>(out request))
                {
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
                        // TODO: clear message and deal with partial transfer on front-end
                        //messages.Clear();
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
        }
    }
}
