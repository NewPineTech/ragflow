import { Layout, theme } from 'antd';
import { Outlet } from 'umi';
import { NextHeaderRight } from './next-header-right';
import { SideBar } from './side-bar';

const { Sider, Content, Header } = Layout;

export default function NextLayout() {
  const {
    token: { colorBgContainer },
  } = theme.useToken();

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      <SideBar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <NextHeaderRight />
        <main className="flex-1 overflow-auto p-6 bg-background">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
