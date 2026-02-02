import { Outlet } from 'umi';
import { SideBar } from './sidebar';

import { cn } from '@/lib/utils';
import styles from './index.less';

const UserSetting = () => {
  return (
    <div className="h-screen w-full flex bg-background overflow-hidden">
      <SideBar />
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <div
          className={cn(
            styles.outletWrapper,
            'flex-1 m-4 rounded-xl border border-border bg-card shadow-sm overflow-auto',
          )}
        >
          <Outlet />
        </div>
      </div>
    </div>
  );
};

export default UserSetting;
