import React from 'react';
import './BrokersAccountModal.css';

interface BrokersAccountModalProps {
  open: boolean;
  onClose: () => void;
  onGoToSetup: () => void;
}

const BrokersAccountModal: React.FC<BrokersAccountModalProps> = ({
  open,
  onClose,
  onGoToSetup,
}) => {
  if (!open) {
    return null;
  }

  const handlePanelClick = (event: React.MouseEvent<HTMLDivElement>) => {
    event.stopPropagation();
  };

  const handleSetup = () => {
    onClose();
    onGoToSetup();
  };

  return (
    <div
      className="brokers-guard-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="brokers-guard-title"
      onClick={onClose}
    >
      <div className="brokers-guard-panel" onClick={handlePanelClick}>
        <h3 id="brokers-guard-title">Paper account selected</h3>
        <p className="brokers-guard-body">
          To start a brokerage session, switch to a connected brokerage account (Schwab,
          IBKR, etc.) from the dropdown.
        </p>
        <div className="brokers-guard-actions">
          <button type="button" className="brokers-guard-primary" onClick={onClose}>
            Select Account
          </button>
          <button type="button" className="brokers-guard-secondary" onClick={handleSetup}>
            Go to Setup
          </button>
        </div>
      </div>
    </div>
  );
};

export default BrokersAccountModal;
