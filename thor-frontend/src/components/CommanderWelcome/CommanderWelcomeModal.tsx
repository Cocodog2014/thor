import React, { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import sceneOneImg from '../../assets/Scene 1.png';
import sceneTwoImg from '../../assets/Scene 2.png';
import './CommanderWelcomeModal.css';

export interface CommanderWelcomeModalProps {
  open: boolean;
  onDismiss: () => void;
}

const modalImages = [sceneOneImg, sceneTwoImg];
const imageDurations = [5000, 3000];

const CommanderWelcomeModal: React.FC<CommanderWelcomeModalProps> = ({ open, onDismiss }) => {
  const [imageIndex, setImageIndex] = useState(0);
  const timerRef = useRef<number | null>(null);

  useEffect(() => {
    if (!open) {
      setImageIndex(0);
      if (timerRef.current) {
        window.clearTimeout(timerRef.current);
      }
      return undefined;
    }

    const scheduleNext = () => {
      timerRef.current = window.setTimeout(() => {
        setImageIndex((prev) => (prev + 1) % modalImages.length);
      }, imageDurations[imageIndex] ?? imageDurations[0]);
    };

    scheduleNext();

    return () => {
      if (timerRef.current) {
        window.clearTimeout(timerRef.current);
      }
    };
  }, [open, imageIndex]);

  if (!open || typeof document === 'undefined') {
    return null;
  }

  return createPortal(
    <div className="commander-modal-overlay" role="dialog" aria-modal="true" aria-label="Command center briefing">
      <div className="commander-modal image-mode">
        <div className="commander-modal__visual">
          <img
            src={modalImages[imageIndex]}
            alt={`Command center scene ${imageIndex + 1}`}
            className="commander-modal__image"
          />
          {imageIndex === 0 && <div className="commander-modal__callout">Captain on deck</div>}
        </div>
        <button type="button" className="commander-modal__dismiss" onClick={onDismiss}>
          Engage
        </button>
      </div>
    </div>,
    document.body,
  );
};

export default CommanderWelcomeModal;
