import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { api } from '../lib/api';
import type { Card, CardStatus } from '../types';

export default function ReviewPage() {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [statusFilter, setStatusFilter] = useState<CardStatus | 'all'>('draft');

  const { data: cards = [], isLoading, refetch } = useQuery({
    queryKey: ['cards', statusFilter],
    queryFn: () =>
      statusFilter === 'all'
        ? api.getCards()
        : api.getCards({ status: statusFilter as CardStatus }),
  });

  const currentCard = cards[currentIndex];

  const updateStatus = async (status: CardStatus) => {
    if (!currentCard) return;

    try {
      await api.updateCardStatus(currentCard.id, status);
      await refetch();

      // Move to next card
      if (currentIndex < cards.length - 1) {
        setCurrentIndex(currentIndex + 1);
      }
    } catch (error) {
      console.error('Failed to update card status:', error);
    }
  };

  const nextCard = () => {
    if (currentIndex < cards.length - 1) {
      setCurrentIndex(currentIndex + 1);
    }
  };

  const prevCard = () => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-muted-foreground">Loading cards...</div>
      </div>
    );
  }

  if (cards.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full space-y-4">
        <div className="text-2xl">📭</div>
        <div className="text-lg font-medium">No cards to review</div>
        <div className="text-muted-foreground">
          Generate some cards to get started!
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex">
      {/* Sidebar */}
      <div className="w-64 border-r bg-muted/10 p-4 overflow-y-auto">
        <div className="space-y-2 mb-4">
          <label className="text-sm font-medium">Filter by status:</label>
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value as CardStatus | 'all');
              setCurrentIndex(0);
            }}
            className="w-full px-3 py-2 border rounded-md"
          >
            <option value="all">All Cards</option>
            <option value="draft">Draft</option>
            <option value="accepted">Accepted</option>
            <option value="rejected">Rejected</option>
          </select>
        </div>

        <div className="space-y-1">
          {cards.map((card, index) => (
            <button
              key={card.id}
              onClick={() => setCurrentIndex(index)}
              className={`w-full text-left px-3 py-2 rounded-md text-sm transition-colors ${
                index === currentIndex
                  ? 'bg-primary text-primary-foreground'
                  : 'hover:bg-muted'
              }`}
            >
              <div className="flex items-center gap-2">
                <StatusIcon status={card.status} />
                <span className="truncate">
                  {card.type === 'basic'
                    ? (card.content as any).front
                    : (card.content as any).text}
                </span>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col">
        <div className="flex-1 p-8 overflow-y-auto">
          <div className="max-w-2xl mx-auto space-y-6">
            <div className="text-sm text-muted-foreground">
              Card {currentIndex + 1} of {cards.length}
            </div>

            {currentCard && (
              <div className="space-y-6">
                {currentCard.type === 'basic' ? (
                  <>
                    <div className="space-y-2">
                      <div className="text-sm font-medium text-muted-foreground">Front:</div>
                      <div className="p-4 bg-card border rounded-lg">
                        {(currentCard.content as any).front}
                      </div>
                    </div>
                    <div className="space-y-2">
                      <div className="text-sm font-medium text-muted-foreground">Back:</div>
                      <div className="p-4 bg-card border rounded-lg">
                        {(currentCard.content as any).back}
                      </div>
                    </div>
                  </>
                ) : (
                  <div className="space-y-2">
                    <div className="text-sm font-medium text-muted-foreground">Cloze Text:</div>
                    <div className="p-4 bg-card border rounded-lg">
                      {(currentCard.content as any).text}
                    </div>
                  </div>
                )}

                {currentCard.tags.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {currentCard.tags.map((tag) => (
                      <span
                        key={tag}
                        className="px-2 py-1 text-xs rounded-full bg-secondary text-secondary-foreground"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="border-t p-4 bg-card">
          <div className="max-w-2xl mx-auto flex items-center justify-between">
            <div className="flex gap-2">
              <button
                onClick={prevCard}
                disabled={currentIndex === 0}
                className="px-4 py-2 border rounded-md disabled:opacity-50"
              >
                ← Previous
              </button>
              <button
                onClick={nextCard}
                disabled={currentIndex === cards.length - 1}
                className="px-4 py-2 border rounded-md disabled:opacity-50"
              >
                Next →
              </button>
            </div>

            <div className="flex gap-2">
              <button
                onClick={() => updateStatus('accepted')}
                className="px-4 py-2 bg-success text-success-foreground rounded-md hover:opacity-90"
              >
                ✓ Accept
              </button>
              <button
                onClick={() => updateStatus('rejected')}
                className="px-4 py-2 bg-destructive text-destructive-foreground rounded-md hover:opacity-90"
              >
                ✗ Reject
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatusIcon({ status }: { status: CardStatus }) {
  switch (status) {
    case 'accepted':
      return <span className="text-success">✓</span>;
    case 'rejected':
      return <span className="text-destructive">✗</span>;
    default:
      return <span className="text-muted-foreground">•</span>;
  }
}
