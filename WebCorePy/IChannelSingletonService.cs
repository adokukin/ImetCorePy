using System.Threading.Channels;

namespace WebCorePy
{
    public struct Message
    {
        public int id;
        public int? source;
        public int target;
        public string session;
        public string value;
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
