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
const SCENE_ONE_DURATION = 6000;
const SCENE_ONE_PHASE_DURATION = 2500;
const CALLOUT_FADE_DURATION = 400;
const SCENE_TWO_MESSAGE_DURATION = 4000;

const CommanderWelcomeModal: React.FC<CommanderWelcomeModalProps> = ({ open, onDismiss }) => {
  const [imageIndex, setImageIndex] = useState(0);
  const [sceneOneStage, setSceneOneStage] = useState<'captain' | 'shield'>('captain');
  const [calloutVisible, setCalloutVisible] = useState(true);
  const [sceneTwoCalloutVisible, setSceneTwoCalloutVisible] = useState(false);
  const timerRef = useRef<number | null>(null);
  const sceneOneTimerRef = useRef<number[]>([]);
  const sceneTwoTimerRef = useRef<number | null>(null);

  const clearSceneOneTimers = () => {
    sceneOneTimerRef.current.forEach((id) => window.clearTimeout(id));
    sceneOneTimerRef.current = [];
  };

  const clearSceneTwoTimer = () => {
    if (sceneTwoTimerRef.current) {
      window.clearTimeout(sceneTwoTimerRef.current);
      sceneTwoTimerRef.current = null;
    }
  };

  useEffect(() => {
    if (!open) {
      setImageIndex(0);
      setSceneOneStage('captain');
      setCalloutVisible(true);
      setSceneTwoCalloutVisible(false);
      clearSceneOneTimers();
      clearSceneTwoTimer();
      if (timerRef.current) {
        window.clearTimeout(timerRef.current);
      }
      return undefined;
    }

    if (imageIndex === 0) {
      timerRef.current = window.setTimeout(() => {
        setImageIndex(1);
      }, SCENE_ONE_DURATION);
    } else if (timerRef.current) {
      window.clearTimeout(timerRef.current);
    }

    return () => {
      if (timerRef.current) {
        window.clearTimeout(timerRef.current);
      }
    };
  }, [open, imageIndex]);

  useEffect(() => {
    if (!open || imageIndex !== 0) {
      clearSceneOneTimers();
      setSceneOneStage('captain');
      setCalloutVisible(true);
      return undefined;
    }

    clearSceneOneTimers();
    setSceneOneStage('captain');
    setCalloutVisible(true);

    const fadeTimer = window.setTimeout(() => {
      setCalloutVisible(false);
    }, SCENE_ONE_PHASE_DURATION);

    const swapTimer = window.setTimeout(() => {
      setSceneOneStage('shield');
      setCalloutVisible(true);
    }, SCENE_ONE_PHASE_DURATION + CALLOUT_FADE_DURATION);

    sceneOneTimerRef.current = [fadeTimer, swapTimer];

    return clearSceneOneTimers;
  }, [open, imageIndex]);

  useEffect(() => {
    if (!open || imageIndex !== 1) {
      clearSceneTwoTimer();
      setSceneTwoCalloutVisible(false);
      return undefined;
    }

    setSceneTwoCalloutVisible(true);
    clearSceneTwoTimer();
    sceneTwoTimerRef.current = window.setTimeout(() => {
      setSceneTwoCalloutVisible(false);
    }, SCENE_TWO_MESSAGE_DURATION);

    return clearSceneTwoTimer;
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
          {imageIndex === 0 && (
            <div
              className={`commander-modal__callout${calloutVisible ? '' : ' is-hidden'}`}
            >
              {sceneOneStage === 'captain' ? 'Captain on deck' : 'Warp Core - Stable   SHEILDS - 100 %'}
            </div>
          )}
          {imageIndex === 1 && (
            <div
              className={`commander-modal__callout commander-modal__callout--scene-two${sceneTwoCalloutVisible ? '' : ' is-hidden'}`}
            >
              Engine room to Captain. Controls are yours.
            </div>
          )}
        </div>
        {imageIndex === 1 && (
          <button type="button" className="commander-modal__dismiss" onClick={onDismiss}>
            Engage
          </button>
        )}
      </div>
    </div>,
    document.body,
  );
};

export default CommanderWelcomeModal;
