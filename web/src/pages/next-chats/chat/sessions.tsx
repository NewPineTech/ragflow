import { MoreButton } from '@/components/more-button';
import { RAGFlowAvatar } from '@/components/ragflow-avatar';
import { Button } from '@/components/ui/button';
import { SearchInput } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useSetModalState } from '@/hooks/common-hooks';
import {
  useFetchDialog,
  useGetChatSearchParams,
} from '@/hooks/use-chat-request';
import { cn } from '@/lib/utils';
import { Routes } from '@/routes';
import {
  ArrowLeft,
  MessageSquare,
  PanelLeftClose,
  PanelRightClose,
  Plus,
  Settings,
} from 'lucide-react';
import { useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'umi';
import { useHandleClickConversationCard } from '../hooks/use-click-card';
import { useSelectDerivedConversationList } from '../hooks/use-select-conversation-list';
import { ConversationDropdown } from './conversation-dropdown';

type SessionProps = Pick<
  ReturnType<typeof useHandleClickConversationCard>,
  'handleConversationCardClick'
> & { switchSettingVisible(): void; hasSingleChatBox: boolean };

export function Sessions({
  hasSingleChatBox,
  handleConversationCardClick,
  switchSettingVisible,
}: SessionProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const {
    list: conversationList,
    addTemporaryConversation,
    removeTemporaryConversation,
    handleInputChange,
    searchString,
  } = useSelectDerivedConversationList();
  const { data } = useFetchDialog();
  const { visible, switchVisible } = useSetModalState(true);

  const handleCardClick = useCallback(
    (conversationId: string, isNew: boolean) => () => {
      handleConversationCardClick(conversationId, isNew);
    },
    [handleConversationCardClick],
  );

  const { conversationId } = useGetChatSearchParams();

  if (!visible) {
    return (
      <div className="w-12 border-r border-sidebar-border bg-sidebar h-full flex flex-col items-center py-6 gap-6 transition-all duration-300">
        <PanelRightClose
          className="cursor-pointer size-5 text-sidebar-foreground hover:text-primary transition-colors"
          onClick={switchVisible}
        />
        <Button
          size="icon"
          variant="ghost"
          className="size-9 rounded-lg text-sidebar-foreground hover:bg-sidebar-accent hover:text-primary"
          onClick={() => navigate(Routes.Chats)}
        >
          <ArrowLeft className="size-5" />
        </Button>
        <Button
          size="icon"
          className="size-9 rounded-lg gradient-primary shadow-glow border-none"
          onClick={addTemporaryConversation}
        >
          <Plus className="size-4" />
        </Button>
      </div>
    );
  }

  return (
    <div className="relative flex flex-col h-full border-r w-[280px] bg-sidebar border-sidebar-border transition-all duration-300">
      <div className="absolute left-0 top-0 bottom-0 w-1 gradient-border opacity-40" />

      {/* Return Section */}
      <div className="px-4 pt-8 pb-2">
        <Button
          variant="ghost"
          className="w-full justify-start gap-3 text-sidebar-foreground hover:bg-sidebar-accent hover:text-foreground group rounded-xl p-3 h-11"
          onClick={() => navigate(Routes.Chats)}
        >
          <div className="p-2 rounded-lg bg-background/50 text-sidebar-foreground group-hover:scale-110 group-hover:text-primary transition-all duration-300 shadow-sm">
            <ArrowLeft className="size-4" />
          </div>
          <span className="text-sm font-semibold tracking-tight">Chat</span>
        </Button>
      </div>

      {/* Header Profile Section */}
      <div className="p-6 pb-4 flex items-center justify-between group px-4">
        <div className="flex gap-3 items-center min-w-0 h-11 px-3">
          <div className="relative">
            <div className="absolute -inset-0.5 bg-gradient-to-r from-primary to-accent-primary rounded-lg blur opacity-20 group-hover:opacity-40 transition duration-500" />
            <RAGFlowAvatar
              avatar={data.icon}
              name={data.name}
              className="size-9 rounded-lg border border-background shadow-sm"
            ></RAGFlowAvatar>
          </div>
          <span className="font-bold tracking-tight text-foreground truncate">
            {data.name}
          </span>
        </div>
        <PanelLeftClose
          className="cursor-pointer size-4 text-sidebar-foreground opacity-50 hover:opacity-100 hover:text-primary transition-all"
          onClick={switchVisible}
        />
      </div>

      <div className="px-4 py-4 space-y-4">
        <div className="px-3">
          <Button
            onClick={addTemporaryConversation}
            className="w-full gradient-primary shadow-glow border-none rounded-xl gap-2 font-semibold h-11"
          >
            <Plus className="size-4" />
            {t('chat.newConversation')}
          </Button>
        </div>

        <div className="relative px-3">
          <SearchInput
            onChange={handleInputChange}
            value={searchString}
            className="bg-background/40 border-sidebar-border/50 rounded-xl h-10 pl-10 focus:ring-1 focus:ring-primary/30"
            placeholder={t('common.search')}
          />
        </div>
      </div>

      <div className="px-7 py-2 flex items-center gap-2">
        <span className="text-[10px] uppercase tracking-widest font-bold text-muted-foreground/60">
          {t('chat.conversations')}
        </span>
        <span className="px-1.5 py-0.5 rounded-full bg-sidebar-accent/50 text-[10px] font-bold text-primary border border-primary/20">
          {conversationList.length}
        </span>
      </div>

      <ScrollArea className="flex-1 px-4 mt-2 font-medium">
        <div className="flex flex-col gap-1.5">
          {conversationList.map((x) => {
            const isActive = conversationId === x.id;
            return (
              <div
                key={x.id}
                onClick={handleCardClick(x.id, x.is_new)}
                className={cn(
                  'relative flex items-center gap-3 w-full px-3 py-2 rounded-xl transition-all duration-300 cursor-pointer group h-11',
                  isActive
                    ? 'bg-sidebar-accent/50 text-foreground'
                    : 'text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-foreground',
                )}
              >
                <div
                  className={cn(
                    'p-2 rounded-lg transition-all duration-300 flex items-center justify-center',
                    isActive
                      ? 'bg-primary text-primary-foreground shadow-glow'
                      : 'bg-background/50 text-sidebar-foreground group-hover:scale-110 group-hover:text-primary',
                  )}
                >
                  <MessageSquare className="size-4" />
                </div>
                <div className="flex-1 truncate text-sm">{x.name}</div>

                <ConversationDropdown
                  conversation={x}
                  removeTemporaryConversation={removeTemporaryConversation}
                >
                  <div className="opacity-0 group-hover:opacity-100 transition-opacity">
                    <MoreButton className="size-6"></MoreButton>
                  </div>
                </ConversationDropdown>

                {isActive && (
                  <div className="absolute left-0 w-1 h-6 bg-primary rounded-r-full shadow-[0_0_8px_hsl(var(--primary))]" />
                )}
              </div>
            );
          })}
        </div>
      </ScrollArea>

      <div className="p-4 border-t border-sidebar-border/50 mt-auto">
        <div className="px-3">
          <Button
            className="w-full h-11 rounded-xl gap-3 text-sm font-semibold border-sidebar-border/50 hover:bg-sidebar-accent transition-all justify-start px-3"
            onClick={switchSettingVisible}
            disabled={!hasSingleChatBox}
            variant={'outline'}
          >
            <div className="p-2 rounded-lg bg-background/50 text-sidebar-foreground group-hover:text-primary transition-all">
              <Settings className="size-4" />
            </div>
            {t('chat.chatSetting')}
          </Button>
        </div>
      </div>
    </div>
  );
}
