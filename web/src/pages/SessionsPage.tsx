import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { api } from '../lib/api';
import { formatDate, formatRelativeTime } from '../lib/utils';
import type { Session } from '../types';

export default function SessionsPage() {
  const queryClient = useQueryClient();

  const { data: sessions = [], isLoading } = useQuery({
    queryKey: ['sessions'],
    queryFn: () => api.getSessions(),
  });

  const deleteSessionMutation = useMutation({
    mutationFn: (sessionId: string) => api.deleteSession(sessionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
    },
    onError: (error) => {
      alert(`Failed to delete session: ${error.message}`);
    },
  });

  const handleDeleteSession = (sessionId: string) => {
    if (confirm('Are you sure you want to delete this session? This cannot be undone.')) {
      deleteSessionMutation.mutate(sessionId);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-muted-foreground">Loading sessions...</div>
      </div>
    );
  }

  if (sessions.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full space-y-4">
        <div className="text-2xl">📚</div>
        <div className="text-lg font-medium">No sessions yet</div>
        <div className="text-muted-foreground">
          Create your first session by generating cards!
        </div>
        <Link
          to="/generate"
          className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:opacity-90"
        >
          Generate Cards
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto p-8">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold">Session History</h1>
        <Link
          to="/generate"
          className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:opacity-90"
        >
          Generate New Cards
        </Link>
      </div>

      <div className="space-y-4">
        {sessions
          .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
          .map((session) => (
            <SessionCard
              key={session.id}
              session={session}
              onDelete={() => handleDeleteSession(session.id)}
              isDeleting={deleteSessionMutation.isPending}
            />
          ))}
      </div>
    </div>
  );
}

function SessionCard({ 
  session, 
  onDelete, 
  isDeleting 
}: { 
  session: Session; 
  onDelete: () => void;
  isDeleting: boolean;
}) {
  const completionRate = session.card_count > 0 
    ? Math.round((session.accepted_count / session.card_count) * 100)
    : 0;

  return (
    <div className="border rounded-lg p-6 bg-card hover:bg-muted/10 transition-colors">
      <div className="flex items-start justify-between">
        <div className="flex-1 space-y-3">
          {/* Header */}
          <div className="flex items-center gap-4">
            <div className="text-lg font-medium">
              {formatDate(session.created_at)}
            </div>
            <div className="flex items-center gap-1 text-sm text-muted-foreground">
              <span>{session.card_count} card{session.card_count !== 1 ? 's' : ''}</span>
              <span>•</span>
              <span>{session.provider}</span>
              {session.completed_at && (
                <>
                  <span>•</span>
                  <span>Completed</span>
                </>
              )}
            </div>
          </div>

          {/* Sources */}
          <div className="space-y-1">
            <div className="text-sm font-medium text-muted-foreground">Sources:</div>
            <div className="text-sm">
              {session.sources.length > 0 ? (
                <div className="space-y-1">
                  {session.sources.slice(0, 3).map((source, index) => (
                    <div key={index} className="truncate">
                      {source}
                    </div>
                  ))}
                  {session.sources.length > 3 && (
                    <div className="text-muted-foreground">
                      +{session.sources.length - 3} more sources
                    </div>
                  )}
                </div>
              ) : (
                <span className="text-muted-foreground">No sources</span>
              )}
            </div>
          </div>

          {/* Card Statistics */}
          <div className="flex items-center gap-6 text-sm">
            <div className="flex items-center gap-2">
              <span className="text-success">✓</span>
              <span>{session.accepted_count} accepted</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-destructive">✗</span>
              <span>{session.rejected_count} rejected</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground">•</span>
              <span>{session.pending_count} pending</span>
            </div>
            {session.card_count > 0 && (
              <div className="text-muted-foreground">
                ({completionRate}% completion rate)
              </div>
            )}
          </div>

          {/* Progress Bar */}
          {session.card_count > 0 && (
            <div className="w-full bg-muted rounded-full h-2">
              <div className="flex h-2 rounded-full overflow-hidden">
                <div
                  className="bg-success"
                  style={{
                    width: `${(session.accepted_count / session.card_count) * 100}%`,
                  }}
                />
                <div
                  className="bg-destructive"
                  style={{
                    width: `${(session.rejected_count / session.card_count) * 100}%`,
                  }}
                />
              </div>
            </div>
          )}

          {/* Timestamp */}
          <div className="text-xs text-muted-foreground">
            Created {formatRelativeTime(session.created_at)}
            {session.completed_at && (
              <span> • Completed {formatRelativeTime(session.completed_at)}</span>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-2 ml-4">
          <Link
            to={`/?session=${session.id}`}
            className="px-3 py-1.5 text-sm border rounded-md hover:bg-muted"
          >
            View
          </Link>
          <button
            onClick={onDelete}
            disabled={isDeleting}
            className="px-3 py-1.5 text-sm border border-destructive text-destructive rounded-md hover:bg-destructive hover:text-destructive-foreground disabled:opacity-50"
          >
            {isDeleting ? 'Deleting...' : 'Delete'}
          </button>
        </div>
      </div>
    </div>
  );
}