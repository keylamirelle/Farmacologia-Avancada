import { useCallback, useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';
import type { School } from '../lib/types';

export function useSchools(options: { activeOnly?: boolean } = {}) {
  const { activeOnly = false } = options;
  const [schools, setSchools] = useState<School[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    let q = supabase.from('schools').select('*').order('name', { ascending: true });
    if (activeOnly) q = q.eq('active', true);
    const { data, error } = await q;
    if (error) setError(error.message);
    else {
      setSchools((data ?? []) as School[]);
      setError(null);
    }
    setLoading(false);
  }, [activeOnly]);

  useEffect(() => {
    refresh();
    const channel = supabase
      .channel('schools-changes')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'schools' }, () => refresh())
      .subscribe();
    return () => {
      supabase.removeChannel(channel);
    };
  }, [refresh]);

  return { schools, loading, error, refresh };
}
