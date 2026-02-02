import EmbedDialog from '@/components/embed-dialog';
import { useShowEmbedModal } from '@/components/embed-dialog/use-show-embed-dialog';
import { PageHeader } from '@/components/page-header';
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from '@/components/ui/breadcrumb';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { SharedFrom } from '@/constants/chat';
import { useSetModalState } from '@/hooks/common-hooks';
import { useNavigatePage } from '@/hooks/logic-hooks/navigate-hooks';
import {
  useFetchConversationList,
  useFetchConversationManually,
  useFetchDialog,
  useGetChatSearchParams,
} from '@/hooks/use-chat-request';
import { IClientConversation } from '@/interfaces/database/chat';
import { cn } from '@/lib/utils';
import { useMount } from 'ahooks';
import { isEmpty } from 'lodash';
import { ArrowUpRight, LogOut, Send } from 'lucide-react';
import { useCallback, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useParams } from 'umi';
import { useHandleClickConversationCard } from '../hooks/use-click-card';
import { ChatSettings } from './app-settings/chat-settings';
import { MultipleChatBox } from './chat-box/multiple-chat-box';
import { SingleChatBox } from './chat-box/single-chat-box';
import { Sessions } from './sessions';
import { useAddChatBox } from './use-add-box';
import { useSwitchDebugMode } from './use-switch-debug-mode';

export default function Chat() {
  const { id } = useParams();
  const { navigateToChatList } = useNavigatePage();
  const { data } = useFetchDialog();
  const { t } = useTranslation();
  const [currentConversation, setCurrentConversation] =
    useState<IClientConversation>({} as IClientConversation);

  const { fetchConversationManually } = useFetchConversationManually();

  const { handleConversationCardClick, controller, stopOutputMessage } =
    useHandleClickConversationCard();
  const { visible: settingVisible, switchVisible: switchSettingVisible } =
    useSetModalState(true);

  const { isDebugMode, switchDebugMode } = useSwitchDebugMode();
  const { removeChatBox, addChatBox, chatBoxIds, hasSingleChatBox } =
    useAddChatBox(isDebugMode);

  const { showEmbedModal, hideEmbedModal, embedVisible, beta } =
    useShowEmbedModal();

  const { conversationId, isNew } = useGetChatSearchParams();

  const { data: dialogList } = useFetchConversationList();

  const currentConversationName = useMemo(() => {
    return dialogList.find((x) => x.id === conversationId)?.name;
  }, [conversationId, dialogList]);

  const fetchConversation: typeof handleConversationCardClick = useCallback(
    async (conversationId, isNew) => {
      if (conversationId && !isNew) {
        const conversation = await fetchConversationManually(conversationId);
        if (!isEmpty(conversation)) {
          setCurrentConversation(conversation);
        }
      }
    },
    [fetchConversationManually],
  );

  const handleSessionClick: typeof handleConversationCardClick = useCallback(
    (conversationId, isNew) => {
      handleConversationCardClick(conversationId, isNew);
      fetchConversation(conversationId, isNew);
    },
    [fetchConversation, handleConversationCardClick],
  );

  useMount(() => {
    fetchConversation(conversationId, isNew === 'true');
  });

  if (isDebugMode) {
    return (
      <section className="pt-14 h-[100vh] pb-24">
        <div className="flex items-center justify-between px-10 pb-5">
          <span className="text-2xl">
            {t('chat.multipleModels')} ({chatBoxIds.length}/3)
          </span>
          <Button variant={'ghost'} onClick={switchDebugMode}>
            {t('chat.exit')} <LogOut />
          </Button>
        </div>
        <MultipleChatBox
          chatBoxIds={chatBoxIds}
          controller={controller}
          removeChatBox={removeChatBox}
          addChatBox={addChatBox}
          stopOutputMessage={stopOutputMessage}
          conversation={currentConversation}
        ></MultipleChatBox>
      </section>
    );
  }

  return (
    <section className="h-full flex w-full bg-background overflow-hidden relative">
      <Sessions
        hasSingleChatBox={hasSingleChatBox}
        handleConversationCardClick={handleSessionClick}
        switchSettingVisible={switchSettingVisible}
      ></Sessions>

      <div className="flex-1 flex flex-col min-w-0 bg-background/30 transition-all duration-300">
        <PageHeader className="px-10 border-b border-border/40 bg-background/50 backdrop-blur-md">
          <Breadcrumb>
            <BreadcrumbList>
              <BreadcrumbItem>
                <BreadcrumbLink onClick={navigateToChatList}>
                  {t('chat.chat')}
                </BreadcrumbLink>
              </BreadcrumbItem>
              <BreadcrumbSeparator />
              <BreadcrumbItem>
                <BreadcrumbPage className="font-semibold text-primary">
                  {data.name}
                </BreadcrumbPage>
              </BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>
          <Button
            onClick={showEmbedModal}
            className="gradient-primary shadow-glow border-none h-10 rounded-xl px-5 font-semibold transition-all"
          >
            <Send className="size-4 mr-2" />
            {t('common.embedIntoSite')}
          </Button>
        </PageHeader>

        <div className="flex-1 flex min-w-0 p-8 pr-10 pb-10 overflow-hidden gap-6">
          <Card className="flex-1 min-w-0 bg-card/40 backdrop-blur-sm border-border/50 shadow-xl rounded-2xl overflow-hidden flex flex-col">
            <CardHeader
              className={cn(
                'px-6 py-4 border-b border-border/40 bg-background/20',
                { 'border-b': hasSingleChatBox },
              )}
            >
              <CardTitle className="flex justify-between items-center text-base">
                <div className="truncate font-semibold tracking-tight">
                  {currentConversationName || t('chat.newConversation')}
                </div>
                <Button
                  variant={'ghost'}
                  onClick={switchDebugMode}
                  className="rounded-lg gap-2 text-primary hover:bg-primary/10 transition-all"
                >
                  <ArrowUpRight className="size-4" /> {t('chat.multipleModels')}
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent className="flex-1 p-0 min-h-0">
              <SingleChatBox
                controller={controller}
                stopOutputMessage={stopOutputMessage}
                conversation={currentConversation}
              ></SingleChatBox>
            </CardContent>
          </Card>
          {settingVisible && (
            <div className="w-[440px] flex shrink-0 overflow-hidden bg-card/30 backdrop-blur-md rounded-2xl border border-border/50 shadow-xl">
              <ChatSettings
                switchSettingVisible={switchSettingVisible}
              ></ChatSettings>
            </div>
          )}
        </div>
      </div>
      {embedVisible && (
        <EmbedDialog
          visible={embedVisible}
          hideModal={hideEmbedModal}
          token={id!}
          from={SharedFrom.Chat}
          beta={beta}
          isAgent={false}
        ></EmbedDialog>
      )}
    </section>
  );
}
