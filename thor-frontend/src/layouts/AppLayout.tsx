import React from 'react';
import GlobalHeader from '../components/Header/GlobalHeader';
import GlobalBanner from '../components/Banners/GlobalBanner';
import { FooterRibbon } from '../components/Ribbons';

type AppLayoutProps = {
  children: React.ReactNode;
};

const AppLayout: React.FC<AppLayoutProps>
  = ({ children }) => {
  return (
    <GlobalHeader 
    >
      {/* Layout: banner (top), scrollable content, ribbon (bottom) */}
      <GlobalBanner />
      <div className="app-content-scroll">
        {children}
      </div>
      <FooterRibbon />
    </GlobalHeader>
  );
};

export default AppLayout;
