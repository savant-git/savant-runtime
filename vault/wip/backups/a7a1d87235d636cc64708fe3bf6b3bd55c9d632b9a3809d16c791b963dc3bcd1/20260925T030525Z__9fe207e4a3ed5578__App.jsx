import React from 'react';
import { AppStateProvider, useAppState } from './contexts/AppStateContext';
import { ErrorBoundary, GlobalErrorInspector } from './components/ErrorDisplay';
import { ThreeScene } from './components/ThreeScene';
import { BootScreen } from './components/BootScreen';
import { CockpitHUD } from './components/CockpitHUD';
import { CRTOverlay } from './components/CRTOverlay';
import { DestinationScreen } from './components/DestinationScreen';
import { CupolaFrame } from './components/CupolaFrame';
import { AnimatePresence, motion } from 'motion/react';

// Cockpit Inner Layout wrapper that implements real-time visual screen vibration
const CockpitLayout: React.FC = () => {
  const { phase, screenShake } = useAppState();

  // CSS transform shake offset calculation mapping to current shake level
  const shakeOffset = screenShake > 0 
    ? {
      transform: `translate(${(Math.random() - 0.5) * screenShake * 3.5}px, ${(Math.random() - 0.5) * screenShake * 3.5}px)`,
      transition: 'transform 0.05s ease-out'
    }
    : undefined;

  return (
    <div 
      className="relative w-full h-screen overflow-hidden bg-black select-none font-mono"
      style={shakeOffset}
    >
      {/* Dynamic CRT CRT-style Scanline and Film-Grain Overlay */}
      <CRTOverlay />

      {/* 3D WebGL Backing Context Render Engine */}
      <ThreeScene />

      {/* Cybernetic Spaceship ISS Cupola Window Frame */}
      {phase === 'BOOT' && (
        <CupolaFrame />
      )}

      {/* Primary HTML Dashboard HUD Interfaces */}
      {(phase === 'BOOT' || phase === 'INIT' || phase === 'FLIGHT') && (
        <div className="absolute inset-0 z-10 transition-all duration-1000 opacity-100 saturate-100 pointer-events-auto">
          <CockpitHUD />
        </div>
      )}

      {phase === 'BOOT' && (
        <div
          className="absolute inset-0 z-20 flex items-center justify-center bg-black/40 backdrop-blur-[2px] pointer-events-auto transition-opacity duration-500"
        >
          <BootScreen />
        </div>
      )}

      {(phase === 'DESTINATION' || phase === 'EXIT') && (
        <div
          className="absolute inset-0 z-10 transition-opacity duration-500"
        >
          <DestinationScreen />
        </div>
      )}

      {/* Floating System log trace debugger drawer */}
      <GlobalErrorInspector />
    </div>
  );
};

export default function App() {
  return (
    <AppStateProvider>
      <ErrorBoundary>
        <CockpitLayout />
      </ErrorBoundary>
    </AppStateProvider>
  );
}
