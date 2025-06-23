using System.Threading.Channels;

namespace WebCorePy
{
    public enum Status
    {
        NEW = 0,
        CHECK,
        CLEAR,
        ACCEPTED,
        BUSY,
        EMPTY,
        IN_PROGRESS,
        READY,
        ERROR
    }

    public struct Message
    {
        public int id;
        public int? source;
        public int? target;
        public string session;
        public string value;
        public Status status;
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
