import React, { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import sceneOneImg from '../../assets/Scene 1.png';
import sceneTwoImg from '../../assets/Scene 2.png';
import sceneThreeImg from '../../assets/Scene 3.png';
import './CommanderWelcomeModal.css';

export interface CommanderWelcomeModalProps {
  open: boolean;
  onDismiss: () => void;
}

const modalImages = [sceneOneImg, sceneTwoImg, sceneThreeImg];
const SCENE_ONE_DURATION = 6000;
const SCENE_ONE_PHASE_DURATION = 2500;
const CALLOUT_FADE_DURATION = 400;
const SCENE_TWO_MESSAGE_DURATION = 4000;
const IMAGE_TRANSITION_DURATION = 900;
const SCENE_THREE_DISPLAY_DURATION = 5000;

const CommanderWelcomeModal: React.FC<CommanderWelcomeModalProps> = ({ open, onDismiss }) => {
  const [imageIndex, setImageIndex] = useState(0);
  const [sceneOneStage, setSceneOneStage] = useState<'captain' | 'shield'>('captain');
  const [calloutVisible, setCalloutVisible] = useState(true);
  const [sceneTwoCalloutVisible, setSceneTwoCalloutVisible] = useState(false);
  const [sceneThreeMessageVisible, setSceneThreeMessageVisible] = useState(false);
  const [isEngaging, setIsEngaging] = useState(false);
  const [previousImageIndex, setPreviousImageIndex] = useState<number | null>(null);
  const timerRef = useRef<number | null>(null);
  const sceneOneTimerRef = useRef<number[]>([]);
  const sceneTwoTimerRef = useRef<number | null>(null);
  const imageTransitionTimerRef = useRef<number | null>(null);
  const sceneThreeTimerRef = useRef<number | null>(null);

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

  const clearImageTransition = () => {
    if (imageTransitionTimerRef.current) {
      window.clearTimeout(imageTransitionTimerRef.current);
      imageTransitionTimerRef.current = null;
    }
    setPreviousImageIndex(null);
  };

  const clearSceneThreeTimer = () => {
    if (sceneThreeTimerRef.current) {
      window.clearTimeout(sceneThreeTimerRef.current);
      sceneThreeTimerRef.current = null;
    }
  };

  useEffect(() => {
    if (!open) {
      setImageIndex(0);
      setSceneOneStage('captain');
      setCalloutVisible(true);
      setSceneTwoCalloutVisible(false);
      setSceneThreeMessageVisible(false);
      setIsEngaging(false);
      clearImageTransition();
      clearSceneOneTimers();
      clearSceneTwoTimer();
      clearSceneThreeTimer();
      if (timerRef.current) {
        window.clearTimeout(timerRef.current);
      }
      return undefined;
    }

    if (imageIndex === 0) {
      timerRef.current = window.setTimeout(() => {
        clearImageTransition();
        setPreviousImageIndex(0);
        setImageIndex(1);
        imageTransitionTimerRef.current = window.setTimeout(() => {
          setPreviousImageIndex(null);
          imageTransitionTimerRef.current = null;
        }, IMAGE_TRANSITION_DURATION);
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
    if (!open || imageIndex !== 1 || isEngaging) {
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
  }, [open, imageIndex, isEngaging]);

  useEffect(() => () => {
    clearSceneThreeTimer();
  }, []);

  const handleEngage = () => {
    if (isEngaging || imageIndex !== 1) {
      return;
    }

    setIsEngaging(true);
    clearSceneTwoTimer();
    clearImageTransition();
    clearSceneThreeTimer();
    setSceneThreeMessageVisible(false);
    setPreviousImageIndex(1);
    setImageIndex(2);

    imageTransitionTimerRef.current = window.setTimeout(() => {
      setPreviousImageIndex(null);
      imageTransitionTimerRef.current = null;
      setSceneThreeMessageVisible(true);
      sceneThreeTimerRef.current = window.setTimeout(() => {
        setSceneThreeMessageVisible(false);
        onDismiss();
      }, SCENE_THREE_DISPLAY_DURATION);
    }, IMAGE_TRANSITION_DURATION);
  };

  if (!open || typeof document === 'undefined') {
    return null;
  }

  return createPortal(
    <div className="commander-modal-overlay" role="dialog" aria-modal="true" aria-label="Command center briefing">
      <div className="commander-modal image-mode">
        <div className="commander-modal__visual">
          {previousImageIndex !== null && (
            <img
              key={`prev-${previousImageIndex}`}
              src={modalImages[previousImageIndex]}
              alt={`Command center scene ${previousImageIndex + 1}`}
              className="commander-modal__image is-exiting"
            />
          )}
          <img
            key={`current-${imageIndex}`}
            src={modalImages[imageIndex]}
            alt={`Command center scene ${imageIndex + 1}`}
            className={`commander-modal__image${previousImageIndex !== null ? ' is-entering' : ' is-active'}`}
          />
          {imageIndex === 0 && (
            <div
              className={`commander-modal__callout${calloutVisible ? '' : ' is-hidden'}`}
            >
              {sceneOneStage === 'captain' ? 'Captain on deck' : 'WARP CORE - STABLE     - SHIELDS - 100%'}
            </div>
          )}
          {imageIndex === 1 && previousImageIndex === null && (
            <div
              className={`commander-modal__callout commander-modal__callout--scene-two${sceneTwoCalloutVisible ? '' : ' is-hidden'}`}
            >
              Engine room to Captain. Controls are yours.
            </div>
          )}
          {imageIndex === 2 && sceneThreeMessageVisible && (
            <div className="commander-modal__callout commander-modal__callout--scene-three">
              <strong>Your war room is activated.</strong>
              <span>The storm accelerates before you.</span>
              <span>Lead with discipline—every move echoes across the battlefield.</span>
            </div>
          )}
        </div>
        {imageIndex === 1 && (
          <button
            type="button"
            className="commander-modal__dismiss"
            onClick={handleEngage}
            disabled={isEngaging}
          >
            Engage
          </button>
        )}
      </div>
    </div>,
    document.body,
  );
};

export default CommanderWelcomeModal;
