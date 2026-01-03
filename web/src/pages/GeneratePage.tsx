import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../lib/api';
import type { CardType, GenerationProgress } from '../types';

export default function GeneratePage() {
  const navigate = useNavigate();
  const [sources, setSources] = useState<string[]>(['']);
  const [provider, setProvider] = useState('openai');
  const [cardTypes, setCardTypes] = useState<CardType[]>(['basic', 'cloze']);
  const [countGuidance, setCountGuidance] = useState('10-15');
  const [tags, setTags] = useState('');
  const [userDirectives, setUserDirectives] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [progress, setProgress] = useState<GenerationProgress | null>(null);

  const addSource = () => {
    setSources([...sources, '']);
  };

  const removeSource = (index: number) => {
    setSources(sources.filter((_, i) => i !== index));
  };

  const updateSource = (index: number, value: string) => {
    const newSources = [...sources];
    newSources[index] = value;
    setSources(newSources);
  };

  const handleGenerate = async () => {
    const validSources = sources.filter((s) => s.trim());
    if (validSources.length === 0) {
      alert('Please add at least one source');
      return;
    }

    setIsGenerating(true);
    setProgress(null);

    try {
      const response = await api.startGeneration({
        sources: validSources,
        provider,
        card_types: cardTypes,
        count_guidance: countGuidance,
        tags: tags.split(',').map((t) => t.trim()).filter(Boolean),
        user_directives: userDirectives || undefined,
      });

      // Connect to WebSocket for progress updates
      const ws = new WebSocket(api.getWebSocketUrl(response.job_id));

      ws.onmessage = (event) => {
        const data: GenerationProgress = JSON.parse(event.data);
        setProgress(data);

        if (data.status === 'complete') {
          ws.close();
          setIsGenerating(false);
          // Redirect to review page after a short delay
          setTimeout(() => navigate('/'), 2000);
        } else if (data.status === 'error') {
          ws.close();
          setIsGenerating(false);
        }
      };

      ws.onerror = () => {
        setIsGenerating(false);
        alert('WebSocket connection error');
      };
    } catch (error) {
      setIsGenerating(false);
      alert(`Generation failed: ${error}`);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-8">
      <h1 className="text-3xl font-bold mb-8">Generate New Cards</h1>

      <div className="space-y-6">
        {/* Sources */}
        <div className="space-y-2">
          <label className="block text-sm font-medium">Sources</label>
          {sources.map((source, index) => (
            <div key={index} className="flex gap-2">
              <input
                type="text"
                value={source}
                onChange={(e) => updateSource(index, e.target.value)}
                placeholder="URL, file path, or text"
                className="flex-1 px-3 py-2 border rounded-md"
                disabled={isGenerating}
              />
              {sources.length > 1 && (
                <button
                  onClick={() => removeSource(index)}
                  className="px-3 py-2 border rounded-md hover:bg-muted"
                  disabled={isGenerating}
                >
                  Remove
                </button>
              )}
            </div>
          ))}
          <button
            onClick={addSource}
            className="px-4 py-2 border rounded-md hover:bg-muted"
            disabled={isGenerating}
          >
            + Add Source
          </button>
        </div>

        {/* Provider */}
        <div className="space-y-2">
          <label className="block text-sm font-medium">LLM Provider</label>
          <select
            value={provider}
            onChange={(e) => setProvider(e.target.value)}
            className="w-full px-3 py-2 border rounded-md"
            disabled={isGenerating}
          >
            <option value="openai">OpenAI (GPT-4)</option>
            <option value="anthropic">Anthropic (Claude)</option>
          </select>
        </div>

        {/* Card Types */}
        <div className="space-y-2">
          <label className="block text-sm font-medium">Card Types</label>
          <div className="flex gap-4">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={cardTypes.includes('basic')}
                onChange={(e) => {
                  if (e.target.checked) {
                    setCardTypes([...cardTypes, 'basic']);
                  } else {
                    setCardTypes(cardTypes.filter((t) => t !== 'basic'));
                  }
                }}
                disabled={isGenerating}
              />
              Basic (Front/Back)
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={cardTypes.includes('cloze')}
                onChange={(e) => {
                  if (e.target.checked) {
                    setCardTypes([...cardTypes, 'cloze']);
                  } else {
                    setCardTypes(cardTypes.filter((t) => t !== 'cloze'));
                  }
                }}
                disabled={isGenerating}
              />
              Cloze Deletion
            </label>
          </div>
        </div>

        {/* Count Guidance */}
        <div className="space-y-2">
          <label className="block text-sm font-medium">Card Count</label>
          <input
            type="text"
            value={countGuidance}
            onChange={(e) => setCountGuidance(e.target.value)}
            placeholder="e.g., 10-15, around 20, comprehensive"
            className="w-full px-3 py-2 border rounded-md"
            disabled={isGenerating}
          />
        </div>

        {/* Tags */}
        <div className="space-y-2">
          <label className="block text-sm font-medium">Tags (comma-separated)</label>
          <input
            type="text"
            value={tags}
            onChange={(e) => setTags(e.target.value)}
            placeholder="e.g., programming, python, algorithms"
            className="w-full px-3 py-2 border rounded-md"
            disabled={isGenerating}
          />
        </div>

        {/* User Directives */}
        <div className="space-y-2">
          <label className="block text-sm font-medium">
            Additional Instructions (Optional)
          </label>
          <textarea
            value={userDirectives}
            onChange={(e) => setUserDirectives(e.target.value)}
            placeholder="e.g., Focus on key concepts and definitions"
            rows={3}
            className="w-full px-3 py-2 border rounded-md"
            disabled={isGenerating}
          />
        </div>

        {/* Generate Button */}
        <button
          onClick={handleGenerate}
          disabled={isGenerating}
          className="w-full px-6 py-3 bg-primary text-primary-foreground rounded-md font-medium hover:opacity-90 disabled:opacity-50"
        >
          {isGenerating ? 'Generating...' : 'Generate Cards'}
        </button>

        {/* Progress */}
        {progress && (
          <div className="mt-6 p-4 border rounded-md space-y-2">
            <div className="font-medium">
              {progress.status === 'complete' ? '✓ Complete!' : 'Generating...'}
            </div>
            {progress.message && (
              <div className="text-sm text-muted-foreground">{progress.message}</div>
            )}
            {progress.progress !== undefined && progress.total !== undefined && (
              <div className="w-full bg-muted rounded-full h-2">
                <div
                  className="bg-primary h-2 rounded-full transition-all"
                  style={{
                    width: `${(progress.progress / progress.total) * 100}%`,
                  }}
                />
              </div>
            )}
            {progress.cards && progress.cards.length > 0 && (
              <div className="text-sm">
                Generated {progress.cards.length} card{progress.cards.length > 1 ? 's' : ''}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
