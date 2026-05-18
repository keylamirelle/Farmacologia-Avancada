import { useCallback, useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';
import type { MovementWithJoins } from '../lib/types';

export function useTodayMovements() {
  const [movements, setMovements] = useState<MovementWithJoins[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchMovements = useCallback(async () => {
    setLoading(true);
    const start = new Date();
    start.setHours(0, 0, 0, 0);

    const { data, error } = await supabase
      .from('stock_movements')
      .select('*, products(name, unit), profiles(display_name)')
      .gte('performed_at', start.toISOString())
      .order('performed_at', { ascending: false });

    if (error) {
      setError(error.message);
    } else {
      setMovements((data ?? []) as unknown as MovementWithJoins[]);
      setError(null);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchMovements();

    const channel = supabase
      .channel('movements-changes')
      .on(
        'postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'stock_movements' },
        () => {
          fetchMovements();
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [fetchMovements]);

  return { movements, loading, error, refresh: fetchMovements };
}
