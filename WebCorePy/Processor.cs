using System;

namespace WebCorePy
{
    public enum State
    {
        EMPTY,
        IN_PROGRESS,
        READY
    }

    public struct Processor
    {
        public string process; // TODO: proper type
        public State state;
        public DateTime? start;
        public DateTime? end;
        public string file_train;
        public string file_test;
        public Processor()
        {
            process = null;
            state = State.EMPTY;
            start = null;
            end = null;
            file_train = null;
            file_test = null;
        }
    }
}
