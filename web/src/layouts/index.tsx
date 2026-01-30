import { Divider, Layout, theme } from 'antd';
import React from 'react';
import { Outlet } from 'umi';
import '../locales/config';
import Header from './components/header';

import styles from './index.less';

const { Content, Sider } = Layout;

const App: React.FC = () => {
  const {
    token: { colorBgContainer, borderRadiusLG },
  } = theme.useToken();

  return (
    <Layout className={styles.layout}>
      <Layout>
        <Sider width={200} style={{ background: colorBgContainer }}>
          <Header />
          <Divider type="horizontal" style={{ margin: 0 }} className={styles.divider} />
        </Sider>
        <Layout>
          <Content
            style={{
              minHeight: 280,
              background: colorBgContainer,
              borderRadius: borderRadiusLG,
              overflow: 'auto',
              display: 'flex',
            }}
          >
            <Outlet />
          </Content>
        </Layout>
      </Layout>
    </Layout>
  );
};

export default App;
