import { useCallback, useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';
import type { Person } from '../lib/types';

export function usePeople(options: { activeOnly?: boolean } = {}) {
  const { activeOnly = false } = options;
  const [people, setPeople] = useState<Person[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    let q = supabase.from('people').select('*').order('name', { ascending: true });
    if (activeOnly) q = q.eq('active', true);
    const { data, error } = await q;
    if (error) setError(error.message);
    else {
      setPeople((data ?? []) as Person[]);
      setError(null);
    }
    setLoading(false);
  }, [activeOnly]);

  useEffect(() => {
    refresh();
    const channel = supabase
      .channel('people-changes')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'people' }, () => refresh())
      .subscribe();
    return () => {
      supabase.removeChannel(channel);
    };
  }, [refresh]);

  return { people, loading, error, refresh };
}
