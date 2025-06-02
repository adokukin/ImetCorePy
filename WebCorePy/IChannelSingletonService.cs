using System.Threading.Channels;

namespace WebCorePy
{
    public struct Message
    {
        int Id;
        int process;
        string value;
    }

    public interface IChannelSingletonService
    {
    }

    public class ChannelSingletonService : IChannelSingletonService
    {
        protected Channel<Message> channel = null;

        public ChannelSingletonService() {
            this.channel = Channel.CreateUnbounded<Message>();
        }
    }
}
