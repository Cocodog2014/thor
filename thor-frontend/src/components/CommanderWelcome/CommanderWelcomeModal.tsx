import React from 'react';
import { createPortal } from 'react-dom';
import './CommanderWelcomeModal.css';

export interface CommanderWelcomeModalProps {
  open: boolean;
  onDismiss: () => void;
}

const CommanderWelcomeModal: React.FC<CommanderWelcomeModalProps> = ({ open, onDismiss }) => {
  if (!open || typeof document === 'undefined') {
    return null;
  }

  return createPortal(
    <div className="commander-modal-overlay" role="dialog" aria-modal="true" aria-label="Welcome back commander">
      <div className="commander-modal">
        <p className="commander-modal__eyebrow">Welcome back, Commander</p>
        <h2>All systems report green. Orders ready for deployment.</h2>
        
        <button type="button" className="commander-modal__dismiss" onClick={onDismiss}>
          Dismiss
        </button>
      </div>
    </div>,
    document.body,
  );
};

export default CommanderWelcomeModal;
