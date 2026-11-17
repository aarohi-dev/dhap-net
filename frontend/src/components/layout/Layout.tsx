import React from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import TopBar from './TopBar';

export const Layout: React.FC = () => {
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#0a0e1a] text-[#e2e8f0]">
      {/* Scan line effect */}
      <div className="scan-line" />

      {/* Persistent Left Sidebar */}
      <Sidebar />

      {/* Main Container */}
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        {/* Top Navigation Bar */}
        <TopBar />

        {/* Dynamic Route Outlet */}
        <main className="flex-1 overflow-y-auto cyber-grid p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
export default Layout;
