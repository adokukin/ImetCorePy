using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
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

        public WorkerRequest(WorkerCommand command)
        {
            this.command = command;
            this.train = false;
            this.test = false ;
            this.algorithms = null;
            this.timeout = 0;
        }

        public WorkerRequest(WorkerCommand command, bool train, bool test, List<string> algorithms, int timeout)
        {
            this.command = command;
            this.train = train;
            this.test = test;
            this.algorithms = algorithms;
            this.timeout = timeout;
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
        private BufferBlock<WorkerRequest> _request_buffer;
        private BufferBlock<WorkerResponse> _response_buffer;

        private int _request_id;

        Process process;
        public WorkerState state;
        public DateTime? start;
        public DateTime? end;
        public string file_train;
        public string file_test;

        List<string> messages = new List<string>();
        decimal progress;

        public PoolWorker(CancellationToken ct)
        {
            this.ct = ct;
            
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

        public WorkerResult Start(WorkerRequest request)
        {
            messages = new List<string>();
            progress = 0;
            
            start = DateTime.Now;
            end = null;

            ProcessStartInfo info = new ProcessStartInfo
            {
                UseShellExecute = false,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                CreateNoWindow = true,
                FileName = "py",
                Arguments = "-3 py/dummy.py"
            };

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
                var test = Decimal.TryParse(line.Data, CultureInfo.InvariantCulture, out progress);
            }
        }

        private void ProcessExited(object sender, EventArgs e)
        {
            process.CancelOutputRead();
            process.CancelErrorRead();
            process.Dispose();
            process = null;

            start = null;
            end = DateTime.Now;
        }

        public void Stop()
        {
            if (process != null)
            {
                process.Kill();
            }

            start = null;
            end = null;
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
                try
                {
                    while(await _request_buffer.OutputAvailableAsync())
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
                            lock (messages)
                            {
                                result = Restart(request);
                                break;
                            }
                        }
                    }
                } 
                catch (OperationCanceledException ex)
                { 
                    break;
                }
            }
        }
    }
}
