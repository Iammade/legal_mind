import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

// PDF mappings constant
const PDF_MAPPINGS = [
  { display: "THE DIVORCE ACT", filename: "Indian Divorce Act_Combine.pdf" },
  { display: "THE INDIAN EVIDENCE ACT", filename: "Indian Evidence Act.pdf" },
  { display: "The Indian Penal Code", filename: "Indian Penal Code.pdf" },
  { display: "THE NEGOTIABLE INSTRUMENTS", filename: "Negotiable Instruments Act.pdf" },
  { display: "THE CODE OF CIVIL PROCEDURE", filename: "THE CODE OF CIVIL PROCEDURE.pdf" },
  { display: "THE CODE OF CRIMINAL PROCEDURE", filename: "THE CODE OF CRIMINAL PROCEDURE.pdf" },
  { display: "THE MOTOR VEHICLES ACT", filename: "The Motor Vehicles Act.pdf" }
];

function App() {
  const [availablePDFs, setAvailablePDFs] = useState([]);
  const [selectedPDF, setSelectedPDF] = useState('');
  const [question, setQuestion] = useState('');
  const [context, setContext] = useState('');
  const [answer, setAnswer] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [processStatus, setProcessStatus] = useState('');

  useEffect(() => {
    fetchPDFs();
  }, []);

  const fetchPDFs = async () => {
    try {
      const response = await axios.get('http://localhost:5000/pdfs');
      setAvailablePDFs(response.data.pdfs);
      setProcessStatus(`Found ${response.data.count} PDFs`);
    } catch (err) {
      setError('Error fetching PDFs');
      setProcessStatus('Failed to load PDFs');
    }
  };

  const handlePDFSelect = async (filename) => {
    if (!filename) {
      setSelectedPDF('');
      setContext('');
      setAnswer('');
      return;
    }

    setLoading(true);
    setError('');
    setProcessStatus('Loading PDF...');
    setContext('');
    setAnswer('');
    setSelectedPDF(filename);

    try {
      const response = await axios.get(`http://localhost:5000/process-pdf/${filename}`);
      setContext(response.data.text);
      const selectedDoc = PDF_MAPPINGS.find(pdf => pdf.filename === filename);
      setProcessStatus(`${selectedDoc?.display || filename} loaded successfully!`);
      setError('');
    } catch (err) {
      setError(err.response?.data?.error || 'Error loading PDF');
      setProcessStatus('Loading failed');
      setContext('');
    } finally {
      setLoading(false);
    }
  };

  const handleAskQuestion = async () => {
    if (!question) {
      setError('Please enter a question');
      return;
    }
    if (!context) {
      setError('Please select a PDF first');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await axios.post('http://localhost:5000/query', {
        question,
        context
      });
      setAnswer(response.data.answer);
      setError('');
    } catch (err) {
      setError(err.response?.data?.error || 'Error processing question');
      setAnswer('');
    } finally {
      setLoading(false);
    }
  };

  const renderAnswerTables = (answer) => {
    return answer.split('\n').map((point, index) => {
      if (!point.trim()) return null;
      
      return (
        <div key={index} className="answer-table mb-4">
          <table className="min-w-full border-collapse">
            <thead>
              
            </thead>
            <tbody>
              <tr>
                <td className="border border-blue-200 px-4 py-3 text-gray-600 text-center">
                  •
                </td>
                <td className="border border-blue-200 px-4 py-3 text-gray-700">
                  {point.trim().replace(/^[•-]\s*/, '')}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      );
    });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-gray-100 py-8 px-4">
      <div className="max-w-4xl mx-auto">
        <div className="bg-white rounded-xl shadow-2xl overflow-hidden">
          <div className="px-8 py-10">
            <h1 className="text-3xl font-bold text-center text-gray-800 mb-10">
              Legal Mind 
            </h1>

            {/* PDF Selection Dropdown */}
            <div className="mb-8">
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Select the question you want to ask about the law 
              </label>
              <select
                value={selectedPDF}
                onChange={(e) => handlePDFSelect(e.target.value)}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg shadow-sm 
                          focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                          bg-white text-gray-700 transition-colors duration-200"
                disabled={loading}
              >
                <option value="">Select a document...</option>
                {PDF_MAPPINGS.map((pdf) => (
                  <option key={pdf.filename} value={pdf.filename}>
                    {pdf.display}
                  </option>
                ))}
              </select>
            </div>

            {processStatus && (
              <div className={`mb-6 p-4 rounded-lg ${
                processStatus.includes('successfully') 
                  ? 'bg-green-50 text-green-700 border border-green-200' 
                  : processStatus.includes('failed')
                    ? 'bg-red-50 text-red-700 border border-red-200'
                    : 'bg-blue-50 text-blue-700 border border-blue-200'
              }`}>
                <p className="text-sm font-medium">{processStatus}</p>
              </div>
            )}

            {/* Question Input Section */}
            <div className="mb-8">
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Ask a Question
              </label>
              <textarea
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="Enter your question about the document..."
                className="w-full px-4 py-3 border border-gray-300 rounded-lg shadow-sm 
                          focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                          min-h-[120px] text-gray-700 transition-colors duration-200"
                disabled={!context || loading}
              />
              <button
                onClick={handleAskQuestion}
                disabled={loading || !context || !question}
                className={`mt-4 w-full py-3 px-6 rounded-lg shadow-sm text-sm font-medium text-white 
                  transition-all duration-200 transform hover:scale-[1.02]
                  ${loading || !context || !question
                    ? 'bg-gray-400 cursor-not-allowed'
                    : 'bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500'
                  }`}
              >
                {loading ? 'Processing...' : 'Ask Question'}
              </button>
            </div>

            {/* Error Display */}
            {error && (
              <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-sm text-red-700 font-medium">{error}</p>
              </div>
            )}

            {/* Answer Display */}
            {answer && (
              <div className="mt-8">
                <h2 className="text-xl font-semibold text-gray-800 mb-4">Answer:</h2>
                <div className="space-y-4 answer-container">
                  {renderAnswerTables(answer)}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;