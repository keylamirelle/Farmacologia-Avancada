import { useCallback, useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';
import type { WithdrawalWithJoins } from '../lib/types';

type Filter = 'active' | 'all' | 'today';

const JOIN_SELECT = '*, people(id, name), schools(id, name), materials(id, name, unit, returnable)';

export function useWithdrawals(filter: Filter = 'active') {
  const [withdrawals, setWithdrawals] = useState<WithdrawalWithJoins[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    let q = supabase
      .from('withdrawals')
      .select(JOIN_SELECT)
      .order('withdrawn_at', { ascending: false });

    if (filter === 'active') {
      q = q.is('returned_at', null);
    } else if (filter === 'today') {
      const start = new Date();
      start.setHours(0, 0, 0, 0);
      q = q.gte('withdrawn_at', start.toISOString());
    }

    const { data, error } = await q;
    if (error) setError(error.message);
    else {
      setWithdrawals((data ?? []) as unknown as WithdrawalWithJoins[]);
      setError(null);
    }
    setLoading(false);
  }, [filter]);

  useEffect(() => {
    refresh();
    const channel = supabase
      .channel(`withdrawals-${filter}`)
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'withdrawals' },
        () => refresh()
      )
      .subscribe();
    return () => {
      supabase.removeChannel(channel);
    };
  }, [refresh, filter]);

  return { withdrawals, loading, error, refresh };
}
