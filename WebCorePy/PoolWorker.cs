using System;
using System.Collections.Concurrent;
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
            _task = null;
            _cts = null;

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
                if (_task == null)
                {
                    return WorkerState.EMPTY;
                }
                else if (_task.IsCompleted) 
                {
                    return WorkerState.READY;
                }
                else
                {
                    return WorkerState.BUSY;
                }
            }
        }

        async Task<WorkerResponse> GetStatus()
        {
            _request_buffer.Post(new WorkerRequest(_request_id++));
            WorkerResponse response = await _response_buffer.ReceiveAsync();
            return response;
        }

        public void Start()
        {
            Cancel(); // outside processor should prevent cancelling important tasks
            _cts = new CancellationTokenSource();
            _task = Task.Run(() => Process(), _cts.Token);
        }

        public void Cancel()
        {
            if (State != WorkerState.EMPTY)
            {
                _cts.Cancel();
                _task = null;
            }
        }

        private void Process() 
        {
            // TODO: run process, manage process output, check _requests_queue 
        }
    }
}
