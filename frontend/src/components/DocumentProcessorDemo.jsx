import { useState } from 'react';
import FileUpload from './FileUpload';
import ProgressBar from './ProgressBar';

/**
 * DocumentProcessorDemo Component
 * 
 * Demonstrates the smooth, seamless state interaction between
 * FileUpload and ProgressBar via React props and state triggers.
 */
export default function DocumentProcessorDemo() {
  const [isUploading, setIsUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [statusText, setStatusText] = useState('');
  const [currentStep, setCurrentStep] = useState(0);
  const [totalSteps] = useState(12);
  const [stepDescription, setStepDescription] = useState('');
  const [isComplete, setIsComplete] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  // Simulation steps representing the deep document ingestion pipeline
  const pipelineSteps = [
    { text: 'Initializing document stream...', desc: 'Verifying package signatures' },
    { text: 'Parsing document metadata...', desc: 'Reading headers, footers & word counts' },
    { text: 'Decompressing archive components...', desc: 'Unzipping OOXML document layers' },
    { text: 'Extracting document XML structure...', desc: 'Isolating document.xml hierarchy' },
    { text: 'Tokenizing text nodes...', desc: 'Chunk 1 of 6 parsed' },
    { text: 'Linguistic parsing...', desc: 'Chunk 2 of 6 parsed' },
    { text: 'Analyzing grammar and syntax...', desc: 'Chunk 3 of 6 parsed' },
    { text: 'Running validation models...', desc: 'Chunk 4 of 6 parsed' },
    { text: 'Classifying semantic entities...', desc: 'Chunk 5 of 6 parsed' },
    { text: 'Refining contextual vector layers...', desc: 'Chunk 6 of 6 parsed' },
    { text: 'Compiling results...', desc: 'Aggregating metrics and metadata' },
    { text: 'Storing structural outputs...', desc: 'Finalizing ingestion payload' }
  ];

  // Triggers when a valid file is chosen via FileUpload
  const handleFileSelect = () => {
    setErrorMessage('');
    setIsComplete(false);
    setProgress(0);
  };

  // Triggers when the file is removed/cleared
  const handleClear = () => {
    setIsUploading(false);
    setProgress(0);
    setIsComplete(false);
    setStatusText('');
    setStepDescription('');
    setCurrentStep(0);
  };

  // Main ingestion process trigger
  const handleUpload = (selectedFile) => {
    if (!selectedFile) return;

    setIsUploading(true);
    setProgress(0);
    setIsComplete(false);
    setCurrentStep(1);
    setStatusText(pipelineSteps[0].text);
    setStepDescription(pipelineSteps[0].desc);

    let stepIndex = 0;
    
    // Simulate complex ingestion processing using timer intervals
    const interval = setInterval(() => {
      stepIndex += 1;
      
      if (stepIndex < pipelineSteps.length) {
        // Calculate progression based on step index
        const calculatedProgress = Math.round((stepIndex / pipelineSteps.length) * 100);
        
        setProgress(calculatedProgress);
        setCurrentStep(stepIndex + 1);
        setStatusText(pipelineSteps[stepIndex].text);
        setStepDescription(pipelineSteps[stepIndex].desc);
      } else {
        // Wrap up processing
        clearInterval(interval);
        setProgress(100);
        setIsComplete(true);
        setIsUploading(false);
      }
    }, 900); // 900ms per simulated ingestion chunk step
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center justify-center p-6 space-y-8">
      {/* Container header */}
      <div className="text-center space-y-2 max-w-md">
        <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-indigo-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">
          Ingestion Dashboard
        </h1>
        <p className="text-sm text-slate-400">
          Upload any Word (.docx) document to parse structure and extract semantic structures instantly.
        </p>
      </div>

      {/* Connection Demonstration */}
      <div className="w-full max-w-xl space-y-6">
        
        {/* FileUpload Component */}
        <FileUpload
          onFileSelect={handleFileSelect}
          onUpload={handleUpload}
          onClear={handleClear}
          isUploading={isUploading}
          externalError={errorMessage}
        />

        {/* ProgressBar Component (only shown when processing or complete) */}
        {(isUploading || isComplete) && (
          <div className="animate-fadeIn transition-all duration-500">
            <ProgressBar
              progress={progress}
              statusText={statusText}
              currentStep={currentStep}
              totalSteps={totalSteps}
              stepDescription={stepDescription}
              isComplete={isComplete}
              title="Save Tarek Ingestion pipeline"
            />
          </div>
        )}
      </div>

      {/* Development Notice */}
      <div className="text-center text-[10px] tracking-widest text-slate-600 uppercase pt-4">
        Ready for production deployment
      </div>
    </div>
  );
}
