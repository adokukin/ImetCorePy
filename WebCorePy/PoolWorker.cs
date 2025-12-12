using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Threading;
using System.Threading.Tasks;
using System.Threading.Tasks.Dataflow;

namespace WebCorePy
{
    public enum WorkerState
    {
        EMPTY,
        BUSY,
        READY
    }

    public struct WorkerRequest
    {
        public int id;

        public WorkerRequest(int id)
        {
            this.id = id;
        }
    }

    public struct WorkerResponse
    {
        public int id;
        public decimal progress;
        public string[] output;

        public WorkerResponse(int id, decimal progress, string[] output)
        {
            this.id = id;
            this.progress = progress;
            this.output = output;
        }
    }

    public class PoolWorker
    {
        private Task _task;
        private CancellationTokenSource _cts;
        private BufferBlock<WorkerRequest> _request_buffer;
        private BufferBlock<WorkerResponse> _response_buffer;

        private int _request_id;

        Process process;
        public WorkerState state;
        public DateTime? start;
        public DateTime? end;
        public string file_train;
        public string file_test;

        List<string> messages;
        decimal progress;

        public PoolWorker()
        {
            _cts = new CancellationTokenSource();
            _task = Task.Run(() => Process(), _cts.Token); // should run always to process status request

            _request_buffer = new BufferBlock<WorkerRequest>();
            _response_buffer = new BufferBlock<WorkerResponse>();
            _request_id = 0;

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

        public async Task<WorkerResponse> GetStatus()
        {
            _request_buffer.Post(new WorkerRequest(_request_id++));
            WorkerResponse response = await _response_buffer.ReceiveAsync();
            return response;
        }

        public void Start()
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
            process.OutputDataReceived += (sender, line) => messages.Add(line.Data);
            process.ErrorDataReceived += (sender, line) => Decimal.TryParse(line.Data, out progress);
            var res = process.Start();
            process.BeginOutputReadLine();
            process.BeginErrorReadLine();

            process.WaitForExit();

            process.CancelOutputRead();
            process.CancelErrorRead();

            start = null;
            end = DateTime.Now;
        }

        public void Stop()
        {
            process.Kill();

            start = null;
            end = null;
        }

        public void Restart()
        {
            Stop();
            Start();
        }

        public void Cancel()
        {
            // stop this thread
            Stop();
            _cts.Cancel();
        }

        private void Process() 
        {
            WorkerRequest request;

            // TODO: run process, manage process output
            while (!_cts.IsCancellationRequested)
            {
                if (_request_buffer.TryReceive<WorkerRequest>(out request))
                {
                    WorkerResponse response = new WorkerResponse(request.id, progress, messages.ToArray());
                    _response_buffer.Post<WorkerResponse>(response);
                    messages.Clear();
                }
            }
        }
    }
}
