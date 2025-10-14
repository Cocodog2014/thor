import React from 'react';

const AuthLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <div style={{ display: 'flex', minHeight: '100vh', alignItems: 'flex-start', justifyContent: 'center' }}>
      <div style={{ width: '100%', maxWidth: 560, marginTop: 64, padding: 16 }}>
        {children}
      </div>
    </div>
  );
};

export default AuthLayout;
