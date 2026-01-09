import React from 'react';
import GlobalHeader from '../components/Header/GlobalHeader';
import GlobalBanner from '../components/Banners/GlobalBanner';
// SAFE MODE: disable FooterRibbon to remove background ticker
// import { FooterRibbon } from '../components/Ribbons';

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
      {/* SAFE MODE: disable FooterRibbon to remove background ticker */}
      {/* <FooterRibbon /> */}
    </GlobalHeader>
  );
};

export default AppLayout;
