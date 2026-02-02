import { useFetchAgentList } from '@/hooks/use-agent-request';
import { useFetchDialogList } from '@/hooks/use-chat-request';
import { useFetchKnowledgeList } from '@/hooks/use-knowledge-request';
import { Bot, Database, MessageSquare, Search } from 'lucide-react';
import { useCallback } from 'react';
import { useNavigate } from 'umi';
import { Applications } from './applications';
import { NextBanner } from './banner';
import { Datasets } from './datasets';
import { QuickActionCard } from './quick-action-card';
import { HomeStatsCard } from './stats-card';

const Home = () => {
  const navigate = useNavigate();
  const { data: agentData, loading: agentLoading } = useFetchAgentList({});
  const { data: dialogData, loading: dialogLoading } = useFetchDialogList();
  const { list: knowledgeList, loading: knowledgeLoading } =
    useFetchKnowledgeList();

  const handleNavigate = useCallback(
    (path: string, search?: string) => {
      navigate({
        pathname: path,
        search: search,
      });
    },
    [navigate],
  );

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-10">
      <NextBanner></NextBanner>

      <section className="px-10 grid grid-cols-1 md:grid-cols-3 gap-4">
        <HomeStatsCard
          label="Total Agents"
          value={agentLoading ? '...' : agentData?.total ?? 0}
          icon={<Bot size={18} />}
        />
        <HomeStatsCard
          label="Total chatbots"
          value={dialogLoading ? '...' : dialogData?.total ?? 0}
          icon={<MessageSquare size={18} />}
        />
        <HomeStatsCard
          label="Total datasets"
          value={knowledgeLoading ? '...' : knowledgeList?.length ?? 0}
          icon={<Database size={18} />}
        />
      </section>

      <section className="px-10 space-y-4">
        <div className="flex items-center gap-2 mb-2">
          <h2 className="text-xl font-bold text-foreground">Quick Actions</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <QuickActionCard
            title="Create AI Agent"
            description="Build a custom AI agent with your own knowledge base and personality"
            icon={<Bot size={24} className="text-white" />}
            gradient
            onClick={() => handleNavigate('/agents', 'isCreate=true')}
          />
          <QuickActionCard
            title="Create New Chat Bot"
            description="Create a new chatbot with your own knowledge base and personality"
            icon={<MessageSquare size={24} className="text-primary" />}
            onClick={() => handleNavigate('/next-chats')}
          />
          <QuickActionCard
            title="Create Dataset"
            description="Upload documents and train your AI on custom data"
            icon={<Database size={24} className="text-primary" />}
            onClick={() => handleNavigate('/datasets', 'isCreate=true')}
          />
          <QuickActionCard
            title="Advanced Search"
            description="Enable AI-powered search across your entire data ecosystem"
            icon={<Search size={24} className="text-primary" />}
            onClick={() => handleNavigate('/next-searches')}
          />
        </div>
      </section>

      <section className="px-10 space-y-8">
        <Applications></Applications>
        <Datasets></Datasets>
      </section>
    </div>
  );
};

export default Home;
