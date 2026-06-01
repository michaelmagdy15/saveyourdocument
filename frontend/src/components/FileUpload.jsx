import { useState, useRef, useEffect } from 'react';

/**
 * Premium FileUpload Component (100% Tailwind-free, Vanilla inline styled)
 */
export default function FileUpload({
  onFileSelect,
  onUpload,
  onClear,
  isUploading = false,
  externalError = ''
}) {
  const [dragActive, setDragActive] = useState(false);
  const [file, setFile] = useState(null);
  const [error, setError] = useState('');
  const inputRef = useRef(null);

  const displayError = error || externalError;

  // Clean error after 5 seconds
  useEffect(() => {
    if (error && !externalError) {
      const timer = setTimeout(() => setError(''), 5000);
      return () => clearTimeout(timer);
    }
  }, [error, externalError]);

  // Validate that the file is a Word document
  const validateFile = (selectedFile) => {
    if (!selectedFile) return false;
    
    const fileName = selectedFile.name || '';
    const fileExtension = fileName.split('.').pop().toLowerCase();
    
    if (fileExtension !== 'docx') {
      setError('Format invalide. Seuls les documents Word (.docx) sont acceptés.');
      return false;
    }
    
    setError('');
    return true;
  };

  // Helper to format bytes
  const formatBytes = (bytes, decimals = 2) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (isUploading) return;

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      if (validateFile(droppedFile)) {
        setFile(droppedFile);
        if (onFileSelect) onFileSelect(droppedFile);
      }
    }
  };

  const handleChange = (e) => {
    e.preventDefault();
    if (isUploading) return;

    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      if (validateFile(selectedFile)) {
        setFile(selectedFile);
        if (onFileSelect) onFileSelect(selectedFile);
      }
    }
  };

  const handleButtonClick = () => {
    if (isUploading) return;
    inputRef.current.click();
  };

  const handleRemove = (e) => {
    e.stopPropagation();
    if (isUploading) return;
    setFile(null);
    setError('');
    if (inputRef.current) inputRef.current.value = '';
    if (onClear) onClear();
  };

  const handleUploadTrigger = () => {
    if (file && onUpload && !isUploading) {
      onUpload(file);
    }
  };

  return (
    <div style={{ width: '100%', maxWidth: '540px', margin: '0 auto', fontFamily: 'inherit' }}>
      {/* Inline styles for custom animations */}
      <style dangerouslySetInnerHTML={{__html: `
        @keyframes subtlePulse {
          0%, 100% { transform: scale(1); opacity: 0.8; }
          50% { transform: scale(1.01); opacity: 1; }
        }
        @keyframes wave {
          0%, 100% { transform: translateY(0px); }
          50% { transform: translateY(-5px); }
        }
        @keyframes borderPulse {
          0%, 100% { border-color: rgba(139, 92, 246, 0.4); box-shadow: 0 0 0 rgba(139, 92, 246, 0); }
          50% { border-color: rgba(139, 92, 246, 0.8); box-shadow: 0 0 12px rgba(139, 92, 246, 0.2); }
        }
        .animate-subtle { animation: subtlePulse 3s infinite ease-in-out; }
        .animate-wave { animation: wave 2.5s infinite ease-in-out; }
        .animate-border-active { animation: borderPulse 2s infinite ease-in-out; }
      `}} />

      {/* Main Container */}
      <div 
        className="glass-panel" 
        style={{ 
          padding: '1.5rem', 
          position: 'relative', 
          overflow: 'hidden',
          border: '1px solid var(--border-glass)',
          borderRadius: '16px',
          boxShadow: 'var(--shadow-glass)'
        }}
      >
        {/* Title & Badge */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
          <div style={{ textAlign: 'left' }}>
            <h3 style={{ fontSize: '1.1rem', margin: 0, fontWeight: 700, color: 'var(--text-vivid)' }}>Dépôt du document</h3>
            <p style={{ fontSize: '0.75rem', margin: '0.25rem 0 0', color: 'var(--text-muted)' }}>Déposez votre rapport pour une analyse et réécriture.</p>
          </div>
          <span style={{ 
            fontSize: '9px', 
            fontWeight: 'bold', 
            letterSpacing: '0.08em', 
            padding: '4px 8px', 
            background: 'hsla(var(--purple-accent-hsl), 0.1)', 
            border: '1px solid var(--border-purple)', 
            color: 'var(--text-purple)', 
            borderRadius: '999px' 
          }}>
            DOCX UNIQUEMENT
          </span>
        </div>

        {/* Upload Zone */}
        {!file ? (
          <div
            onDragEnter={handleDrag}
            onDragOver={handleDrag}
            onDragLeave={handleDrag}
            onDrop={handleDrop}
            onClick={handleButtonClick}
            className={dragActive ? 'animate-border-active' : ''}
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              border: dragActive ? '2px dashed var(--purple-accent)' : '2px dashed var(--border-glass-bright)',
              borderRadius: '12px',
              padding: '2.5rem 1.5rem',
              textAlign: 'center',
              cursor: 'pointer',
              minHeight: '200px',
              backgroundColor: 'rgba(255, 255, 255, 0.01)',
              transition: 'all 0.3s ease'
            }}
          >
            <input
              ref={inputRef}
              type="file"
              style={{ display: 'none' }}
              accept=".docx"
              onChange={handleChange}
              disabled={isUploading}
            />

            {/* Cloud Icon */}
            <div 
              className={dragActive ? 'animate-wave' : ''}
              style={{
                padding: '0.75rem',
                borderRadius: '50%',
                backgroundColor: 'rgba(255, 255, 255, 0.03)',
                border: '1px solid var(--border-glass)',
                color: 'var(--text-muted)',
                marginBottom: '1rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transition: 'all 0.3s ease'
              }}
            >
              <svg 
                xmlns="http://www.w3.org/2000/svg" 
                fill="none" 
                viewBox="0 0 24 24" 
                strokeWidth="1.5" 
                stroke="currentColor" 
                style={{ width: '32px', height: '32px', color: 'var(--purple-accent)' }}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 16.5V9.75m0 0l3 3m-3-3l-3 3M6.75 19.5a4.5 4.5 0 01-1.41-8.775 5.25 5.25 0 0110.233-2.33 3 3 0 013.758 3.848A3.752 3.752 0 0118 19.5H6.75z" />
              </svg>
            </div>

            <p style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>
              {dragActive ? 'Déposez le fichier ici' : 'Glissez-déposez votre document Word ici'}
            </p>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.35rem', marginBottom: 0 }}>
              ou <span style={{ color: 'var(--purple-accent)', textDecoration: 'underline', fontWeight: 600 }}>parcourez vos fichiers</span>
            </p>

            <div style={{ marginTop: '1rem', display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '10px', color: 'var(--text-muted)' }}>
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="2.0" stroke="currentColor" style={{ width: '12px', height: '12px' }}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12c0 1.268-.63 2.39-1.593 3.068a3.745 3.745 0 01-1.043 3.296 3.745 3.745 0 01-3.296 1.043A3.745 3.745 0 0110 21c-1.268 0-2.39-.63-3.068-1.593a3.746 3.746 0 01-3.296-1.043 3.745 3.745 0 01-1.043-3.296A3.745 3.745 0 013 12c0-1.268.63-2.39 1.593-3.068a3.745 3.745 0 011.043-3.296 3.746 3.746 0 013.296-1.043A3.746 3.746 0 0114 3c1.268 0 2.39.63 3.068 1.593a3.746 3.746 0 013.296 1.043 3.746 3.746 0 011.043 3.296A3.745 3.745 0 0121 12z" />
              </svg>
              <span>Taille maximale : 25 Mo</span>
            </div>
          </div>
        ) : (
          /* File Selected / Ready State */
          <div 
            style={{ 
              border: '1px solid var(--border-purple)', 
              backgroundColor: 'rgba(255, 255, 255, 0.01)', 
              borderRadius: '12px', 
              padding: '1.25rem',
              transition: 'all 0.3s ease'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'start', gap: '1rem' }}>
              {/* Premium Word DOCX Icon */}
              <div 
                className="animate-subtle"
                style={{
                  padding: '0.75rem',
                  backgroundColor: 'rgba(139, 92, 246, 0.08)',
                  border: '1px solid var(--border-purple)',
                  color: 'var(--purple-accent)',
                  borderRadius: '10px',
                  position: 'relative',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0
                }}
              >
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor" style={{ width: '32px', height: '32px' }}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                </svg>
                <div style={{ 
                  position: 'absolute', 
                  bottom: '3px', 
                  right: '3px', 
                  backgroundColor: 'var(--purple-accent)', 
                  color: '#fff', 
                  fontSize: '7px', 
                  fontWeight: 'bold', 
                  padding: '1px 3px', 
                  borderRadius: '2px' 
                }}>W</div>
              </div>

              {/* File Info */}
              <div style={{ flex: 1, minWidth: 0, textAlign: 'left' }}>
                <h4 style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-primary)', margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {file.name}
                </h4>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.25rem' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{formatBytes(file.size)}</span>
                  <span style={{ width: '4px', height: '4px', borderRadius: '50%', backgroundColor: 'rgba(255,255,255,0.2)' }}></span>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Document Word</span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.75rem', color: 'var(--text-emerald)', marginTop: '0.5rem' }}>
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="2.5" stroke="currentColor" style={{ width: '12px', height: '12px' }}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                  </svg>
                  <span style={{ fontWeight: 600 }}>Fichier validé et prêt</span>
                </div>
              </div>

              {/* Remove Button */}
              <button
                onClick={handleRemove}
                disabled={isUploading}
                aria-label="Remove file"
                style={{
                  padding: '0.25rem',
                  backgroundColor: 'transparent',
                  border: 'none',
                  color: 'var(--text-muted)',
                  cursor: 'pointer',
                  borderRadius: '6px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  transition: 'all 0.2s'
                }}
                onMouseOver={(e) => { e.currentTarget.style.color = '#ef4444'; e.currentTarget.style.backgroundColor = 'rgba(239, 68, 68, 0.08)'; }}
                onMouseOut={(e) => { e.currentTarget.style.color = 'var(--text-muted)'; e.currentTarget.style.backgroundColor = 'transparent'; }}
              >
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="2.0" stroke="currentColor" style={{ width: '16px', height: '16px' }}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Action Buttons */}
            <div style={{ marginTop: '1.5rem', paddingTop: '1rem', borderTop: '1px solid var(--border-glass)', display: 'flex', justifyContent: 'end', gap: '0.75rem' }}>
              <button
                onClick={handleRemove}
                disabled={isUploading}
                className="btn btn-outline btn-sm"
              >
                Annuler
              </button>

              <button
                onClick={handleUploadTrigger}
                disabled={isUploading}
                className="btn btn-primary btn-sm"
              >
                {isUploading ? 'Ingestion...' : 'Analyser le document'}
              </button>
            </div>
          </div>
        )}

        {/* Error Alert Box */}
        {displayError && (
          <div 
            style={{ 
              marginTop: '1rem', 
              display: 'flex', 
              alignItems: 'start', 
              gap: '0.75rem', 
              backgroundColor: 'rgba(239, 68, 68, 0.06)', 
              border: '1px solid rgba(239, 68, 68, 0.15)', 
              color: 'var(--color-error)', 
              borderRadius: '8px', 
              padding: '0.75rem 1rem',
              textAlign: 'left'
            }}
          >
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="2.0" stroke="currentColor" style={{ width: '18px', height: '18px', flexShrink: 0, color: 'var(--color-error)' }}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m0-10.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.75c0 5.592 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.57-.598-3.75h-.152c-3.196 0-6.1-1.249-8.25-3.286zm0 13.036h.008v.008H12v-.008z" />
            </svg>
            <div style={{ fontSize: '0.75rem', lineHeight: '1.4' }}>
              <span style={{ fontWeight: 'bold', display: 'block', color: '#fca5a5', marginBottom: '0.15rem' }}>Erreur d&apos;ingestion</span>
              {displayError}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
