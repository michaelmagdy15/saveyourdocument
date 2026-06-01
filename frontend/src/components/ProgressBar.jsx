
/**
 * Premium ProgressBar Component (100% Tailwind-free, Vanilla inline styled with modern CSS)
 * Supports both horizontal (default) and circular progress indicators.
 */
export default function ProgressBar({
  progress = 0,
  statusText = 'Initialisation du processus...',
  status, // Fallback status for App.jsx compatibility
  currentStep,
  totalSteps,
  stepDescription = '',
  isComplete = false,
  isCompleted, // Fallback for App.jsx compatibility
  hasError = false, // Support error states from App.jsx
  title = "Moteur d'ingestion IA",
  variant = 'horizontal' // 'horizontal' | 'circular'
}) {
  const roundedProgress = Math.min(Math.max(Math.round(progress), 0), 100);
  const actualIsComplete = isComplete || isCompleted || roundedProgress === 100;
  const activeProgress = actualIsComplete ? 100 : roundedProgress;
  const showCompletedState = actualIsComplete || activeProgress === 100;
  const displayStatusText = status || statusText;

  // Miniature timeline stages
  const pipelineStages = [
    { name: 'Upload', minProgress: 0, maxProgress: 15 },
    { name: 'Analyse', minProgress: 16, maxProgress: 45 },
    { name: 'Réécriture', minProgress: 46, maxProgress: 80 },
    { name: 'Compilation', minProgress: 81, maxProgress: 100 }
  ];

  return (
    <div style={{ width: '100%', maxWidth: '540px', margin: '0 auto', fontFamily: 'inherit' }}>
      {/* Custom Styles Injection */}
      <style dangerouslySetInnerHTML={{__html: `
        @keyframes pulseGlow {
          0%, 100% { opacity: 0.35; filter: blur(8px); }
          50% { opacity: 0.6; filter: blur(12px); }
        }
        @keyframes shimmerEffect {
          0% { background-position: -200% 0; }
          100% { background-position: 200% 0; }
        }
        @keyframes borderPulseGreen {
          0%, 100% { border-color: rgba(16, 185, 129, 0.2); }
          50% { border-color: rgba(16, 185, 129, 0.6); }
        }
        @keyframes borderPulseRed {
          0%, 100% { border-color: rgba(239, 68, 68, 0.2); }
          50% { border-color: rgba(239, 68, 68, 0.6); }
        }
        @keyframes slideUpFadeIn {
          0% {
            opacity: 0;
            transform: translateY(12px) scale(0.98);
          }
          100% {
            opacity: 1;
            transform: translateY(0) scale(1);
          }
        }
        @keyframes emeraldPulseGlow {
          0%, 100% {
            box-shadow: 0 4px 20px rgba(16, 185, 129, 0.12), inset 0 0 10px rgba(16, 185, 129, 0.03);
            border-color: rgba(16, 185, 129, 0.25);
          }
          50% {
            box-shadow: 0 4px 28px rgba(16, 185, 129, 0.24), inset 0 0 15px rgba(16, 185, 129, 0.08);
            border-color: rgba(52, 211, 153, 0.45);
          }
        }
        @keyframes pulseIndicator {
          0%, 100% { transform: scale(1); opacity: 0.8; }
          50% { transform: scale(1.15); opacity: 1; }
        }
        .animate-pulse-glow { animation: pulseGlow 2.5s infinite ease-in-out; }
        .animate-shimmer {
          background-size: 200% 100%;
          animation: shimmerEffect 2.5s infinite linear;
        }
        .animate-border-green { animation: borderPulseGreen 2s infinite ease-in-out; }
        .animate-border-red { animation: borderPulseRed 2s infinite ease-in-out; }
        .success-card-premium {
          animation: slideUpFadeIn 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards, emeraldPulseGlow 3s infinite ease-in-out;
        }
        .pulse-indicator-dot {
          animation: pulseIndicator 2s infinite ease-in-out;
        }
      `}} />

      {/* Progress Container Card */}
      <div 
        className={hasError ? 'animate-border-red' : showCompletedState ? 'animate-border-green' : ''}
        style={{
          position: 'relative',
          overflow: 'hidden',
          backgroundColor: 'rgba(15, 23, 42, 0.45)',
          backdropFilter: 'blur(12px)',
          borderRadius: '16px',
          padding: '1.5rem',
          border: hasError
            ? '1px solid rgba(239, 68, 68, 0.3)'
            : showCompletedState 
              ? '1px solid rgba(16, 185, 129, 0.3)' 
              : '1px solid var(--border-glass, rgba(255, 255, 255, 0.08))',
          boxShadow: 'var(--shadow-glass, 0 8px 32px 0 rgba(0, 0, 0, 0.37))',
          transition: 'all 0.5s ease'
        }}
      >
        {/* Subtle Ambient light beam overlay */}
        <div 
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            height: '2px',
            background: hasError
              ? 'linear-gradient(to right, transparent, var(--rose-accent, #ef4444), transparent)'
              : showCompletedState 
                ? 'linear-gradient(to right, transparent, var(--emerald-accent, #10b981), transparent)' 
                : 'linear-gradient(to right, transparent, var(--purple-accent, #8b5cf6), transparent)',
            transition: 'all 0.5s ease'
          }}
        ></div>

        {/* Header Metadata Section */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '1.25rem' }}>
          <div style={{ textAlign: 'left' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span 
                className={showCompletedState || hasError ? '' : 'pulse-indicator-dot'}
                style={{
                  width: '8px',
                  height: '8px',
                  borderRadius: '50%',
                  backgroundColor: hasError
                    ? 'var(--rose-accent, #ef4444)'
                    : showCompletedState 
                      ? 'var(--emerald-accent, #10b981)' 
                      : 'var(--purple-accent, #8b5cf6)',
                  display: 'inline-block',
                  boxShadow: hasError
                    ? '0 0 6px var(--rose-accent, #ef4444)'
                    : showCompletedState 
                      ? '0 0 6px var(--emerald-accent, #10b981)' 
                      : '0 0 6px var(--purple-accent, #8b5cf6)'
                }}
              ></span>
              <h4 style={{ fontSize: '10px', fontWeight: 'bold', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-muted, #94a3b8)', margin: 0 }}>
                {title}
              </h4>
            </div>
            
            <h3 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-primary, #f8fafc)', marginTop: '0.35rem', marginBottom: 0 }}>
              {hasError ? 'Erreur de traitement' : showCompletedState ? 'Traitement terminé' : displayStatusText}
            </h3>
          </div>

          {/* Stepper counters */}
          <div style={{ textAlign: 'right' }}>
            <span style={{ 
              fontSize: '1.5rem', 
              fontWeight: 900, 
              fontFamily: 'monospace', 
              color: 'var(--text-vivid, #ffffff)', 
              textShadow: hasError
                ? '0 0 8px rgba(239, 68, 68, 0.3)'
                : showCompletedState 
                  ? '0 0 8px rgba(16, 185, 129, 0.3)' 
                  : '0 0 8px rgba(139, 92, 246, 0.3)' 
            }}>
              {activeProgress}%
            </span>
            {currentStep && totalSteps && (
              <div style={{ fontSize: '9px', fontWeight: 'bold', color: 'var(--purple-accent, #8b5cf6)', marginTop: '0.15rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Étape {currentStep} sur {totalSteps}
              </div>
            )}
          </div>
        </div>

        {/* Detailed Stepper/Description Info Label */}
        {stepDescription && !showCompletedState && !hasError && (
          <div 
            style={{ 
              marginBottom: '1.25rem', 
              display: 'flex', 
              justifyContent: 'space-between', 
              fontSize: '11px', 
              color: 'var(--text-secondary, #cbd5e1)', 
              backgroundColor: 'rgba(0, 0, 0, 0.2)', 
              border: '1px solid var(--border-glass, rgba(255, 255, 255, 0.08))', 
              padding: '0.5rem 0.75rem', 
              borderRadius: '8px' 
            }}
          >
            <span style={{ fontFamily: 'monospace', color: 'var(--text-muted, #94a3b8)' }}>Journal :</span>
            <span style={{ fontWeight: 500 }}>{stepDescription}</span>
          </div>
        )}

        {/* Progress Display Mode */}
        {variant === 'circular' ? (
          /* CIRCULAR VARIANT */
          <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', marginBottom: '1.5rem', position: 'relative' }}>
            {/* SVG Wrapper with ambient glow shadows */}
            <div style={{ position: 'relative', width: '120px', height: '120px' }}>
              <svg width="120" height="120" viewBox="0 0 120 120" style={{ transform: 'rotate(-90deg)', overflow: 'visible' }}>
                <defs>
                  {/* Subtle blur for outer ambient glow */}
                  <filter id="circularGlowFilter" x="-20%" y="-20%" width="140%" height="140%">
                    <feGaussianBlur stdDeviation="5" result="blur" />
                    <feComposite in="SourceGraphic" in2="blur" operator="over" />
                  </filter>
                  <linearGradient id="circularProgressGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor={hasError ? 'var(--rose-accent, #ef4444)' : showCompletedState ? 'var(--emerald-accent, #10b981)' : 'var(--purple-accent, #8b5cf6)'} />
                    <stop offset="100%" stopColor={hasError ? '#f87171' : showCompletedState ? '#34d399' : 'var(--cyan-accent, #06b6d4)'} />
                  </linearGradient>
                </defs>
                {/* Background circle track */}
                <circle
                  cx="60"
                  cy="60"
                  r="48"
                  stroke="rgba(0, 0, 0, 0.4)"
                  strokeWidth="8"
                  fill="transparent"
                  style={{ stroke: 'rgba(255, 255, 255, 0.05)' }}
                />
                {/* Ambient glowing shadow beneath progress path */}
                {activeProgress > 0 && (
                  <circle
                    cx="60"
                    cy="60"
                    r="48"
                    stroke={hasError ? 'var(--rose-accent, #ef4444)' : showCompletedState ? 'var(--emerald-accent, #10b981)' : 'var(--purple-accent, #8b5cf6)'}
                    strokeWidth="10"
                    strokeDasharray={2 * Math.PI * 48}
                    strokeDashoffset={2 * Math.PI * 48 * (1 - activeProgress / 100)}
                    strokeLinecap="round"
                    fill="transparent"
                    filter="url(#circularGlowFilter)"
                    opacity="0.55"
                    style={{
                      transition: 'stroke-dashoffset 0.5s ease-out',
                    }}
                  />
                )}
                {/* Active progress circle path */}
                <circle
                  cx="60"
                  cy="60"
                  r="48"
                  stroke="url(#circularProgressGradient)"
                  strokeWidth="8"
                  strokeDasharray={2 * Math.PI * 48}
                  strokeDashoffset={2 * Math.PI * 48 * (1 - activeProgress / 100)}
                  strokeLinecap="round"
                  fill="transparent"
                  style={{
                    transition: 'stroke-dashoffset 0.5s ease-out',
                  }}
                />
              </svg>
              {/* Central Text displaying actual percentage value */}
              <div style={{
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'center',
                alignItems: 'center',
                color: 'var(--text-primary, #f8fafc)',
              }}>
                <span style={{ fontSize: '1.25rem', fontWeight: 900, fontFamily: 'monospace' }}>
                  {activeProgress}%
                </span>
                <span style={{ fontSize: '8px', textTransform: 'uppercase', color: 'var(--text-muted, #94a3b8)', fontWeight: 'bold', letterSpacing: '0.05em', marginTop: '-2px' }}>
                  {hasError ? 'Erreur' : showCompletedState ? 'Fait' : 'Ingestion'}
                </span>
              </div>
            </div>
          </div>
        ) : (
          /* HORIZONTAL VARIANT (DEFAULT) */
          <div style={{ position: 'relative', marginBottom: '1.5rem' }}>
            {/* Ambient Shadow Layer beneath the progress bar track */}
            <div style={{
              position: 'absolute',
              top: '2px',
              left: '2px',
              right: '2px',
              bottom: '-4px',
              borderRadius: '999px',
              background: hasError
                ? 'linear-gradient(to right, rgba(239, 68, 68, 0.4), rgba(248, 113, 113, 0.4))'
                : showCompletedState
                  ? 'linear-gradient(to right, rgba(16, 185, 129, 0.4), rgba(52, 211, 153, 0.4))'
                  : 'linear-gradient(to right, rgba(139, 92, 246, 0.45), rgba(6, 182, 212, 0.45))',
              filter: 'blur(10px)',
              opacity: 0.8,
              transition: 'all 0.5s ease-out',
              width: `${activeProgress}%`,
              pointerEvents: 'none'
            }} />

            {/* The Actual Progress Bar Track */}
            <div 
              style={{ 
                position: 'relative', 
                height: '10px', 
                width: '100%', 
                backgroundColor: 'rgba(0,0,0,0.4)', 
                borderRadius: '999px', 
                padding: '2px', 
                border: '1px solid var(--border-glass, rgba(255, 255, 255, 0.08))', 
              }}
            >
              {/* Fluid percentage bar fill */}
              <div
                style={{ 
                  width: `${activeProgress}%`,
                  height: '100%',
                  borderRadius: '999px',
                  position: 'relative',
                  background: hasError
                    ? 'linear-gradient(to right, var(--rose-accent, #ef4444), #f87171)'
                    : showCompletedState
                      ? 'linear-gradient(to right, var(--emerald-accent, #10b981), hsl(152, 90%, 65%))'
                      : 'linear-gradient(to right, var(--purple-accent, #8b5cf6), var(--cyan-accent, #06b6d4))',
                  transition: 'all 0.5s ease-out'
                }}
                className="animate-shimmer"
              >
                {/* Edge glow spark */}
                {activeProgress > 0 && activeProgress < 100 && (
                  <span style={{ 
                    position: 'absolute', 
                    top: '50%', 
                    right: 0, 
                    transform: 'translateY(-50%)', 
                    width: '10px', 
                    height: '10px', 
                    borderRadius: '50%', 
                    backgroundColor: '#fff', 
                    boxShadow: '0 0 8px #fff',
                    opacity: 0.8 
                  }}></span>
                )}
              </div>

              {/* Underlying Ambient Glow layer within track */}
              <div
                style={{ 
                  width: `${activeProgress}%`,
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  height: '100%',
                  borderRadius: '999px',
                  background: hasError
                    ? 'var(--rose-accent, #ef4444)'
                    : showCompletedState 
                      ? 'var(--emerald-accent, #10b981)' 
                      : 'var(--purple-accent, #8b5cf6)',
                  transition: 'all 0.5s ease-out',
                  pointerEvents: 'none',
                  opacity: 0.4
                }}
                className="animate-pulse-glow"
              ></div>
            </div>
          </div>
        )}

        {/* Stepper track progress alignment */}
        <div style={{ position: 'relative', width: '100%', paddingTop: '0.75rem', borderTop: '1px solid var(--border-glass, rgba(255, 255, 255, 0.08))', marginTop: '0.5rem' }}>
          {/* Stepper Track Line (gray background) */}
          <div style={{
            position: 'absolute',
            top: '20px', // center of the 14px dots (paddingTop 12px + 7px)
            left: '20px',
            right: '20px',
            height: '2px',
            backgroundColor: 'rgba(255, 255, 255, 0.1)',
            borderRadius: '2px',
            zIndex: 0
          }} />
          
          {/* Active Glowing Stepper Fill Line */}
          <div style={{
            position: 'absolute',
            top: '20px',
            left: '20px',
            width: `calc((${Math.min(activeProgress, 100)} / 100) * (100% - 40px))`,
            height: '2px',
            background: hasError
              ? 'var(--rose-accent, #ef4444)'
              : showCompletedState
                ? 'var(--emerald-accent, #10b981)'
                : 'linear-gradient(to right, var(--purple-accent, #8b5cf6), var(--cyan-accent, #06b6d4))',
            boxShadow: hasError
              ? '0 0 8px var(--rose-accent, #ef4444)'
              : showCompletedState
                ? '0 0 8px var(--emerald-accent, #10b981)'
                : '0 0 8px var(--purple-accent, #8b5cf6)',
            borderRadius: '2px',
            zIndex: 0,
            transition: 'all 0.5s ease-out'
          }} />

          {/* Flex row container for the steps */}
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            position: 'relative',
            zIndex: 1
          }}>
            {pipelineStages.map((stage, idx) => {
              const isStageActive = activeProgress >= stage.minProgress;
              const isStageComplete = activeProgress > stage.maxProgress || showCompletedState;
              
              return (
                <div key={idx} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: '60px' }}>
                  {/* Visual Dot Indicator */}
                  <div 
                    style={{ 
                      width: '14px', 
                      height: '14px', 
                      borderRadius: '50%', 
                      border: '2px solid',
                      borderColor: hasError
                        ? 'var(--rose-accent, #ef4444)'
                        : isStageComplete 
                          ? 'var(--emerald-accent, #10b981)' 
                          : isStageActive
                            ? 'var(--purple-accent, #8b5cf6)'
                            : 'rgba(255, 255, 255, 0.2)',
                      backgroundColor: hasError
                        ? 'var(--rose-accent, #ef4444)'
                        : isStageComplete 
                          ? 'var(--emerald-accent, #10b981)' 
                          : isStageActive
                            ? 'var(--purple-accent, #8b5cf6)'
                            : 'rgba(15, 23, 42, 0.9)',
                      color: '#fff',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      boxShadow: isStageActive 
                        ? (hasError
                            ? '0 0 10px rgba(239, 68, 68, 0.6)'
                            : isStageComplete 
                              ? '0 0 10px rgba(16, 185, 129, 0.6)' 
                              : '0 0 10px rgba(139, 92, 246, 0.6)')
                        : 'none',
                      transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)'
                    }}
                  >
                    {isStageComplete && !hasError ? (
                      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" style={{ width: '8px', height: '8px' }}>
                        <path fillRule="evenodd" d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z" clipRule="evenodd" />
                      </svg>
                    ) : (
                      <span style={{ width: '4px', height: '4px', borderRadius: '50%', backgroundColor: isStageActive ? '#fff' : 'rgba(255, 255, 255, 0.4)', transition: 'all 0.3s' }}></span>
                    )}
                  </div>

                  {/* Stage Label */}
                  <span 
                    style={{ 
                      fontSize: '10px', 
                      fontWeight: 600, 
                      letterSpacing: '0.02em', 
                      marginTop: '0.5rem', 
                      textAlign: 'center',
                      color: hasError
                        ? '#ef4444'
                        : isStageComplete 
                          ? '#10b981' 
                          : isStageActive
                            ? '#a78bfa'
                            : 'var(--text-muted, #94a3b8)',
                      transition: 'color 0.4s'
                    }}
                  >
                    {stage.name}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Complete Notification Splash */}
        {showCompletedState && !hasError && (
          <div 
            className="success-card-premium"
            style={{ 
              marginTop: '1.5rem', 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'space-between', 
              borderRadius: '12px', 
              padding: '1rem 1.25rem',
              textAlign: 'left'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <div style={{ padding: '0.35rem', backgroundColor: 'rgba(16, 185, 129, 0.2)', borderRadius: '50%', color: 'var(--emerald-accent, #10b981)', display: 'flex', boxShadow: '0 0 10px rgba(16, 185, 129, 0.4)' }}>
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="2.5" stroke="currentColor" style={{ width: '18px', height: '18px' }}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12c0 1.268-.63 2.39-1.593 3.068a3.745 3.745 0 01-1.043 3.296 3.745 3.745 0 01-3.296 1.043A3.745 3.745 0 0110 21c-1.268 0-2.39-.63-3.068-1.593a3.746 3.746 0 01-3.296-1.043 3.745 3.745 0 01-1.043-3.296A3.745 3.745 0 013 12c0-1.268.63-2.39 1.593-3.068a3.745 3.745 0 011.043-3.296 3.746 3.746 0 013.296-1.043A3.746 3.746 0 0114 3c1.268 0 2.39.63 3.068 1.593a3.746 3.746 0 013.296 1.043 3.746 3.746 0 011.043 3.296A3.745 3.745 0 0121 12z" />
                </svg>
              </div>
              <div style={{ fontSize: '11.5px', lineHeight: '1.45' }}>
                <span style={{ fontWeight: 'bold', display: 'block', color: '#a7f3d0', fontSize: '12px' }}>Analyse complétée</span>
                Toutes les sections ont été réécrites avec succès.
              </div>
            </div>
            
            <span style={{ 
              fontSize: '9px', 
              fontWeight: 800, 
              textTransform: 'uppercase', 
              letterSpacing: '0.08em', 
              backgroundColor: 'rgba(16, 185, 129, 0.2)', 
              color: '#34d399',
              padding: '3px 10px', 
              borderRadius: '999px', 
              border: '1px solid rgba(16, 185, 129, 0.4)',
              boxShadow: '0 0 8px rgba(16, 185, 129, 0.2)'
            }}>
              COMPILÉ
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
