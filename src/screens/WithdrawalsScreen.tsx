import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  FlatList,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { WithdrawalCard } from '../components/WithdrawalCard';
import { useWithdrawals } from '../hooks/useWithdrawals';
import { supabase } from '../lib/supabase';
import type { RootStackParamList } from '../navigation/RootNavigator';

type Nav = NativeStackNavigationProp<RootStackParamList>;
type Filter = 'active' | 'today' | 'all';

export function WithdrawalsScreen() {
  const nav = useNavigation<Nav>();
  const [filter, setFilter] = useState<Filter>('active');
  const { withdrawals, loading, refresh } = useWithdrawals(filter);

  async function markReturned(id: string) {
    Alert.alert('Confirmar devolução', 'Marcar este material como devolvido?', [
      { text: 'Cancelar', style: 'cancel' },
      {
        text: 'Confirmar',
        onPress: async () => {
          const { error } = await supabase
            .from('withdrawals')
            .update({ returned_at: new Date().toISOString() })
            .eq('id', id);
          if (error) Alert.alert('Erro', error.message);
        },
      },
    ]);
  }

  return (
    <View style={styles.container}>
      <View style={styles.headerRow}>
        <Text style={styles.title}>Retiradas</Text>
        <Pressable style={styles.newBtn} onPress={() => nav.navigate('NewWithdrawal')}>
          <Text style={styles.newBtnText}>+ Nova retirada</Text>
        </Pressable>
      </View>

      <View style={styles.filters}>
        <FilterBtn label="Ativas" active={filter === 'active'} onPress={() => setFilter('active')} />
        <FilterBtn label="Hoje" active={filter === 'today'} onPress={() => setFilter('today')} />
        <FilterBtn label="Todas" active={filter === 'all'} onPress={() => setFilter('all')} />
      </View>

      {loading && withdrawals.length === 0 ? (
        <ActivityIndicator style={{ marginTop: 24 }} />
      ) : (
        <FlatList
          data={withdrawals}
          keyExtractor={(w) => w.id}
          contentContainerStyle={{ paddingBottom: 24 }}
          refreshControl={<RefreshControl refreshing={loading} onRefresh={refresh} />}
          renderItem={({ item }) => (
            <WithdrawalCard
              withdrawal={item}
              onReturnPress={() => markReturned(item.id)}
            />
          )}
          ListEmptyComponent={
            <Text style={styles.empty}>
              {filter === 'active'
                ? 'Nenhuma retirada ativa.'
                : filter === 'today'
                ? 'Nenhuma retirada registrada hoje.'
                : 'Nenhuma retirada registrada ainda.'}
            </Text>
          }
        />
      )}
    </View>
  );
}

function FilterBtn({
  label,
  active,
  onPress,
}: {
  label: string;
  active: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable
      onPress={onPress}
      style={[styles.filterBtn, active && styles.filterBtnActive]}
    >
      <Text style={[styles.filterText, active && styles.filterTextActive]}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16, backgroundColor: '#f9fafb' },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 12,
  },
  title: { fontSize: 24, fontWeight: '700' },
  newBtn: {
    backgroundColor: '#2563eb',
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 8,
  },
  newBtnText: { color: '#fff', fontWeight: '600' },
  filters: { flexDirection: 'row', gap: 6, marginBottom: 12 },
  filterBtn: {
    flex: 1,
    padding: 8,
    borderRadius: 8,
    backgroundColor: '#e5e7eb',
    alignItems: 'center',
  },
  filterBtnActive: { backgroundColor: '#2563eb' },
  filterText: { color: '#374151', fontWeight: '600', fontSize: 13 },
  filterTextActive: { color: '#fff' },
  empty: { textAlign: 'center', marginTop: 32, color: '#6b7280' },
});
