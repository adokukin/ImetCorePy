using System;
using System.Collections.Generic;
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

        public string process; // TODO: proper type
        public WorkerState state;
        public DateTime? start;
        public DateTime? end;
        public string file_train;
        public string file_test;
     
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
            // outside processor should deal with data integrity
            // TODO: run calculating process
            start = DateTime.Now;
            end = null;
        }

        public void Stop()
        {
            // TODO: stop calculating process
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
            int count = 0;
            int total = 300;
            List<string> messages = new List<string> ();
            WorkerRequest request;

            // TODO: run process, manage process output
            while (!_cts.IsCancellationRequested && (count < total))
            {
                Thread.Sleep(1000);
                count++;
                // TODO: get process responses
                messages.Add($"remains {total - count} s");

                // TODO: adjust waiting time
                if (_request_buffer.TryReceive<WorkerRequest>(out request))
                {
                    WorkerResponse response = new WorkerResponse(request.id, (decimal)count / (decimal)total, messages.ToArray());
                    _response_buffer.Post<WorkerResponse>(response);
                    messages.Clear();
                }
            }
        }
    }
}
