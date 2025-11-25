using System.Threading.Channels;

namespace WebCorePy
{
    public enum Status
    {
        START = 0,
        CHECK,
        CLEAR,

        OK, // same as READY or IN_PROGRESS after a command 
        READY,
        BUSY,
        ERROR
    }

    public struct Message
    {
        public int id;
        public int? source;
        public int? target;
        public string session;
        public WorkerResponse? value;
        public Status status;

        public Message()
        {
            id = 0; 
            source = null;
            target = null;
            session = null;
            value = null;
            status = Status.ERROR;
        }
    }

    public interface IChannelSingletonService
    {
        public Channel<Message> channel { get; }
    }

    public class ChannelSingletonService : IChannelSingletonService
    {
        private Channel<Message> _channel = null;


        public ChannelSingletonService() {
            this._channel = System.Threading.Channels.Channel.CreateUnbounded<Message>();
        }

        public Channel<Message> channel { get => _channel; }
    }
}
