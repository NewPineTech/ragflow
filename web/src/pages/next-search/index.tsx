import { useFetchTokenListBeforeOtherStep } from '@/components/embed-dialog/use-show-embed-dialog';
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
import { SharedFrom } from '@/constants/chat';
import { useNavigatePage } from '@/hooks/logic-hooks/navigate-hooks';
import {
  useFetchTenantInfo,
  useFetchUserInfo,
} from '@/hooks/use-user-setting-request';
import { cn } from '@/lib/utils';
import { Routes } from '@/routes';
import { ArrowLeft, Send, Settings } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'umi';
import {
  ISearchAppDetailProps,
  useFetchSearchDetail,
} from '../next-searches/hooks';
import EmbedAppModal from './embed-app-modal';
import { useCheckSettings } from './hooks';
import './index.less';
import SearchHome from './search-home';
import { SearchSetting } from './search-setting';
import SearchingPage from './searching';

export default function SearchPage() {
  const navigate = useNavigate();
  const { navigateToSearchList } = useNavigatePage();
  const [isSearching, setIsSearching] = useState(false);
  const { data: SearchData } = useFetchSearchDetail();
  const { beta, handleOperate } = useFetchTokenListBeforeOtherStep();

  const [openSetting, setOpenSetting] = useState(false);
  const [openEmbed, setOpenEmbed] = useState(false);
  const [searchText, setSearchText] = useState('');
  const { data: tenantInfo } = useFetchTenantInfo();
  const { data: userInfo } = useFetchUserInfo();
  const tenantId = tenantInfo.tenant_id;
  const { t } = useTranslation();
  const { openSetting: checkOpenSetting } = useCheckSettings(
    SearchData as ISearchAppDetailProps,
  );
  useEffect(() => {
    setOpenSetting(checkOpenSetting);
  }, [checkOpenSetting]);

  useEffect(() => {
    if (isSearching) {
      setOpenSetting(false);
    }
  }, [isSearching]);

  return (
    <section className="h-full flex flex-col bg-background overflow-hidden relative">
      <PageHeader className="px-10 border-b border-border/40 bg-background/50 backdrop-blur-md">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="icon"
            className="size-9 rounded-xl bg-background/50 text-sidebar-foreground hover:text-primary transition-all duration-300 shadow-sm border border-border/20 group"
            onClick={() => navigate(Routes.Searches)}
          >
            <ArrowLeft className="size-4 group-hover:scale-110 transition-transform" />
          </Button>
          <Breadcrumb>
            <BreadcrumbList>
              <BreadcrumbItem>
                <BreadcrumbLink onClick={navigateToSearchList}>
                  {t('header.search')}
                </BreadcrumbLink>
              </BreadcrumbItem>
              <BreadcrumbSeparator />
              <BreadcrumbItem>
                <BreadcrumbPage className="font-semibold text-primary">
                  {SearchData?.name}
                </BreadcrumbPage>
              </BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>
        </div>
        <Button
          className="gradient-primary shadow-glow border-none h-10 rounded-xl px-5 font-semibold transition-all"
          onClick={() => {
            handleOperate().then((res) => {
              if (res) {
                setOpenEmbed(!openEmbed);
              }
            });
          }}
        >
          <Send className="size-4 mr-2" />
          {t('search.embedApp')}
        </Button>
      </PageHeader>
      <div className="flex-1 flex gap-3 w-full bg-background overflow-hidden relative">
        <div className="flex-1 overflow-auto">
          {!isSearching && (
            <div className="animate-fade-in-down h-full flex flex-col items-center justify-center p-6">
              <SearchHome
                setIsSearching={setIsSearching}
                isSearching={isSearching}
                searchText={searchText}
                setSearchText={setSearchText}
                userInfo={userInfo}
                canSearch={!checkOpenSetting}
              />
            </div>
          )}
          {isSearching && (
            <div className="animate-fade-in-up">
              <SearchingPage
                setIsSearching={setIsSearching}
                searchText={searchText}
                setSearchText={setSearchText}
                data={SearchData as ISearchAppDetailProps}
              />
            </div>
          )}
        </div>
        {openSetting && (
          <div className="w-[450px] border-l border-border/40 bg-sidebar/50 backdrop-blur-md overflow-auto">
            <SearchSetting
              open={openSetting}
              setOpen={setOpenSetting}
              data={SearchData as ISearchAppDetailProps}
            />
          </div>
        )}
        <EmbedAppModal
          open={openEmbed}
          setOpen={setOpenEmbed}
          url="/next-search/share"
          token={SearchData?.id as string}
          from={SharedFrom.Search}
          tenantId={tenantId}
          beta={beta}
        />
      </div>

      {!isSearching && (
        <div className="absolute left-8 bottom-8">
          <Button
            variant="ghost"
            className={cn(
              'gap-2 px-4 py-6 rounded-2xl bg-sidebar/40 border border-sidebar-border/30 backdrop-blur-md shadow-lg hover:bg-sidebar/60 transition-all',
              openSetting &&
                'bg-primary/10 text-primary border-primary/20 shadow-glow-sm',
            )}
            onClick={() => setOpenSetting(!openSetting)}
          >
            <Settings
              className={cn(
                'size-5',
                openSetting
                  ? 'text-primary animate-spin-slow'
                  : 'text-muted-foreground',
              )}
            />
            <span
              className={cn(
                'font-semibold',
                openSetting ? 'text-primary' : 'text-muted-foreground',
              )}
            >
              {t('search.searchSettings')}
            </span>
          </Button>
        </div>
      )}
    </section>
  );
}
