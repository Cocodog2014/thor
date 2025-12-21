import React from 'react';
import { createPortal } from 'react-dom';
import sceneOneImg from '../../../assets/Scene 1.png';
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
    <div className="commander-modal-overlay" role="dialog" aria-modal="true" aria-label="Command center briefing">
      <div className="commander-modal image-mode">
        <div className="commander-modal__visual">
          <img
            src={sceneOneImg}
            alt="Command center scene"
            className="commander-modal__image is-active"
          />
          <div className="commander-modal__callout">
            Captain on deck — shields at 100%
          </div>
        </div>
        <button
          type="button"
          className="commander-modal__dismiss"
          onClick={onDismiss}
        >
          Engage
        </button>
      </div>
    </div>,
    document.body,
  );
};

export default CommanderWelcomeModal;
