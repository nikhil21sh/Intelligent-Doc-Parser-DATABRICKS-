/**
 * frontend/src/App.jsx
 *
 * Changes from original:
 *  - Destructures `isLive` and `facilityMap` from useFacilities()
 *  - Passes `isLive` to StatsBar
 *  - Passes `facilityMap` to ChatInterface (flows down to CitationPanel)
 *  - Everything else unchanged
 */
import React, { useState, useEffect } from 'react';
import Sidebar        from './components/UI/Sidebar';
import StatsBar       from './components/UI/StatsBar';
import LoadingScreen  from './components/UI/LoadingScreen';
import MapView        from './components/Map/MapView';
import ChatInterface  from './components/Chat/ChatInterface';
import AnomalyPanel   from './components/Anomaly/AnomalyPanel';
import PlanningWizard from './components/Planning/PlanningWizard';
import FacilityCard   from './components/Facility/FacilityCard';
import DemoPanel      from './components/Demo/DemoPanel';
import { useFacilities } from './hooks/useFacilities';
import './styles/index.css';

export default function App() {
  // isLive and facilityMap are new — all other returns unchanged
  const { facilities, anomalies, desertZones, facilityMap, loading, isLive } = useFacilities();

  const [activeTab,      setActiveTab]      = useState('map');
  const [selectedFacility, setSelected]     = useState(null);
  const [demoMode,       setDemoMode]       = useState(false);
  const [showDemoPanel,  setShowDemoPanel]  = useState(false);
  const [demoQuery,      setDemoQuery]      = useState(null);

  const [splash, setSplash] = useState(true);
  useEffect(() => {
    const t = setTimeout(() => setSplash(false), 2800);
    return () => clearTimeout(t);
  }, []);

  function handleDemoToggle() {
    if (!demoMode) {
      setDemoMode(true);
      setShowDemoPanel(true);
    } else {
      setDemoMode(false);
      setShowDemoPanel(false);
    }
  }

  function handleDemoQuery(q) {
    setShowDemoPanel(false);
    setActiveTab('chat');
    setTimeout(() => setDemoQuery(q), 200);
  }

  if (splash || loading) return <LoadingScreen />;

  return (
    <div className="flex h-screen overflow-hidden mesh-bg">
      <Sidebar
        activeTab={activeTab}
        onTabChange={(tab) => { setActiveTab(tab); setSelected(null); }}
        anomalyCount={anomalies.length}
        demoMode={demoMode}
        onDemoToggle={handleDemoToggle}
      />

      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        {/* isLive prop added */}
        <StatsBar facilities={facilities} anomalies={anomalies} isLive={isLive} />

        <div className="flex flex-1 min-h-0 overflow-hidden">

          {activeTab === 'map' && (
            <>
              <div className="flex-1 relative min-w-0">
                <MapView
                  facilities={facilities}
                  desertZones={desertZones}
                  onSelectFacility={(f) => setSelected(f)}
                />
              </div>
              {selectedFacility && (
                <div className="w-80 border-l border-surface-border overflow-y-auto bg-surface-light p-3 shrink-0 animate-slide-up">
                  <FacilityCard
                    facility={selectedFacility}
                    onClose={() => setSelected(null)}
                  />
                </div>
              )}
            </>
          )}

          {activeTab === 'chat' && (
            <div className="flex-1 min-w-0 flex">
              <div className="flex-1 min-w-0">
                {/* facilityMap passed down so CitationPanel can resolve live row_ids */}
                <ChatInterface
                  demoQuery={demoQuery}
                  onDemoQueryConsumed={() => setDemoQuery(null)}
                  facilityMap={facilityMap}
                />
              </div>
            </div>
          )}

          {activeTab === 'anomalies' && (
            <div className="flex-1 overflow-y-auto min-w-0 max-w-2xl mx-auto w-full">
              <div className="p-4 pb-0">
                <h2 className="font-display text-xl font-bold text-white">Anomaly Detection</h2>
                <p className="text-sm text-slate-500 mt-1">
                  AI-flagged facilities with critical resource gaps or irregularities
                </p>
              </div>
              <AnomalyPanel anomalies={anomalies} />
            </div>
          )}

          {activeTab === 'planning' && (
            <div className="flex-1 overflow-hidden min-w-0 max-w-xl mx-auto w-full flex flex-col">
              <div className="p-4 pb-0 shrink-0">
                <h2 className="font-display text-xl font-bold text-white">Planning Wizard</h2>
                <p className="text-sm text-slate-500 mt-1">
                  Model intervention strategies for medical deserts
                </p>
              </div>
              <div className="flex-1 overflow-hidden min-h-0">
                <PlanningWizard />
              </div>
            </div>
          )}
        </div>
      </div>

      {showDemoPanel && (
        <DemoPanel
          onQuery={handleDemoQuery}
          onClose={() => setShowDemoPanel(false)}
        />
      )}

      {demoMode && !showDemoPanel && (
        <div className="fixed top-0 left-1/2 -translate-x-1/2 z-40 px-4 py-1 bg-accent-500/90 text-white text-[11px] font-semibold tracking-wide rounded-b-lg shadow-glow-amber flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" />
          DEMO MODE ACTIVE
          <button
            onClick={() => setShowDemoPanel(true)}
            className="underline ml-1 opacity-80 hover:opacity-100"
          >
            Show Queries
          </button>
        </div>
      )}
    </div>
  );
}