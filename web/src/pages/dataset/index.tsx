import { PageHeader } from '@/components/page-header';
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from '@/components/ui/breadcrumb';
import { useNavigatePage } from '@/hooks/logic-hooks/navigate-hooks';
import { useFetchKnowledgeBaseConfiguration } from '@/hooks/use-knowledge-request';
import { useTranslation } from 'react-i18next';
import { Outlet } from 'umi';
import Generate from './dataset/generate-button/generate';
import { SideBar } from './sidebar';

export default function DatasetWrapper() {
  const { navigateToDatasetList } = useNavigatePage();
  const { t } = useTranslation();
  const { data } = useFetchKnowledgeBaseConfiguration();

  return (
    <section className="flex h-full w-full bg-background overflow-hidden relative">
      <SideBar></SideBar>
      <div className="flex-1 flex flex-col min-h-0 bg-background/30 transition-all duration-300">
        <PageHeader className="px-10 border-b border-border/40 bg-background/50 backdrop-blur-md">
          <Breadcrumb>
            <BreadcrumbList>
              <BreadcrumbItem>
                <BreadcrumbLink onClick={() => navigateToDatasetList({})}>
                  {t('knowledgeDetails.dataset')}
                </BreadcrumbLink>
              </BreadcrumbItem>
              <BreadcrumbSeparator />
              <BreadcrumbItem>
                <BreadcrumbPage className="max-w-[200px] truncate font-semibold text-primary">
                  {data.name}
                </BreadcrumbPage>
              </BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>
          <div className="flex items-center gap-4">
            <Generate disabled={!(data.chunk_num > 0)} />
          </div>
        </PageHeader>
        <div className="flex-1 overflow-auto backdrop-blur-sm">
          <Outlet />
        </div>
      </div>
    </section>
  );
}
