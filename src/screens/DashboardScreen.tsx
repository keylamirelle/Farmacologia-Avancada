import { useMemo, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { MaterialSummaryCard } from '../components/MaterialSummaryCard';
import { useMaterialStatus } from '../hooks/useMaterials';
import { useWithdrawals } from '../hooks/useWithdrawals';
import type { WithdrawalWithJoins } from '../lib/types';

type Tab = 'material' | 'pessoa' | 'escola';

export function DashboardScreen() {
  const [tab, setTab] = useState<Tab>('material');
  const { items: materials, loading: loadingMaterials, refresh: refreshMaterials } =
    useMaterialStatus();
  const { withdrawals: active, loading: loadingActive, refresh: refreshActive } =
    useWithdrawals('active');

  const summary = useMemo(() => {
    const totalUnits = materials.reduce((s, m) => s + Number(m.total_quantity), 0);
    const inUse = materials.reduce((s, m) => s + Number(m.in_use), 0);
    const available = materials.reduce((s, m) => s + Math.max(0, Number(m.available)), 0);
    return { totalUnits, inUse, available };
  }, [materials]);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Dashboard</Text>

      <View style={styles.summaryRow}>
        <SummaryStat label="Materiais" value={materials.length} color="#111" />
        <SummaryStat label="Em uso" value={summary.inUse} color="#b45309" />
        <SummaryStat label="Retiradas ativas" value={active.length} color="#2563eb" />
      </View>

      <View style={styles.tabs}>
        <TabButton label="Por material" active={tab === 'material'} onPress={() => setTab('material')} />
        <TabButton label="Por pessoa" active={tab === 'pessoa'} onPress={() => setTab('pessoa')} />
        <TabButton label="Por escola" active={tab === 'escola'} onPress={() => setTab('escola')} />
      </View>

      {tab === 'material' && (
        <MaterialList
          materials={materials}
          loading={loadingMaterials}
          onRefresh={() => {
            refreshMaterials();
            refreshActive();
          }}
        />
      )}
      {tab === 'pessoa' && (
        <GroupedList active={active} loading={loadingActive} onRefresh={refreshActive} groupBy="person" />
      )}
      {tab === 'escola' && (
        <GroupedList active={active} loading={loadingActive} onRefresh={refreshActive} groupBy="school" />
      )}
    </View>
  );
}

function SummaryStat({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <View style={styles.summaryStat}>
      <Text style={[styles.summaryValue, { color }]}>{value}</Text>
      <Text style={styles.summaryLabel}>{label}</Text>
    </View>
  );
}

function TabButton({
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
      style={[styles.tabBtn, active && styles.tabBtnActive]}
    >
      <Text style={[styles.tabText, active && styles.tabTextActive]}>{label}</Text>
    </Pressable>
  );
}

function MaterialList({
  materials,
  loading,
  onRefresh,
}: {
  materials: ReturnType<typeof useMaterialStatus>['items'];
  loading: boolean;
  onRefresh: () => void;
}) {
  if (loading && materials.length === 0) {
    return <ActivityIndicator style={{ marginTop: 24 }} />;
  }
  return (
    <FlatList
      data={materials}
      keyExtractor={(m) => m.id}
      contentContainerStyle={{ paddingBottom: 24 }}
      refreshControl={<RefreshControl refreshing={loading} onRefresh={onRefresh} />}
      renderItem={({ item }) => <MaterialSummaryCard item={item} />}
      ListEmptyComponent={
        <Text style={styles.empty}>
          Nenhum material cadastrado ainda. Vá em Cadastros para começar.
        </Text>
      }
    />
  );
}

type GroupBy = 'person' | 'school';

type Group = {
  key: string;
  label: string;
  items: WithdrawalWithJoins[];
  totalUnits: number;
};

function GroupedList({
  active,
  loading,
  onRefresh,
  groupBy,
}: {
  active: WithdrawalWithJoins[];
  loading: boolean;
  onRefresh: () => void;
  groupBy: GroupBy;
}) {
  const groups = useMemo<Group[]>(() => {
    const map = new Map<string, Group>();
    for (const w of active) {
      const key =
        groupBy === 'person' ? w.people?.id ?? 'none' : w.schools?.id ?? 'none';
      const label =
        groupBy === 'person'
          ? w.people?.name ?? '(sem responsavel)'
          : w.schools?.name ?? '(sem escola)';
      const existing = map.get(key);
      if (existing) {
        existing.items.push(w);
        existing.totalUnits += Number(w.quantity);
      } else {
        map.set(key, { key, label, items: [w], totalUnits: Number(w.quantity) });
      }
    }
    return Array.from(map.values()).sort((a, b) => a.label.localeCompare(b.label, 'pt-BR'));
  }, [active, groupBy]);

  if (loading && active.length === 0) {
    return <ActivityIndicator style={{ marginTop: 24 }} />;
  }

  return (
    <FlatList
      data={groups}
      keyExtractor={(g) => g.key}
      contentContainerStyle={{ paddingBottom: 24 }}
      refreshControl={<RefreshControl refreshing={loading} onRefresh={onRefresh} />}
      renderItem={({ item }) => <GroupCard group={item} />}
      ListEmptyComponent={
        <Text style={styles.empty}>Nenhuma retirada ativa no momento.</Text>
      }
    />
  );
}

function GroupCard({ group }: { group: Group }) {
  return (
    <View style={styles.groupCard}>
      <View style={styles.groupHeader}>
        <Text style={styles.groupLabel}>{group.label}</Text>
        <Text style={styles.groupCount}>
          {group.items.length} {group.items.length === 1 ? 'retirada' : 'retiradas'}
        </Text>
      </View>
      {group.items.map((w) => (
        <View key={w.id} style={styles.groupItem}>
          <Text style={styles.groupItemText}>
            {w.materials?.name ?? '(material)'} —{' '}
            <Text style={{ fontWeight: '700' }}>
              {w.quantity} {w.materials?.unit ?? ''}
            </Text>
          </Text>
          <Text style={styles.groupItemMeta}>
            {new Date(w.withdrawn_at).toLocaleString('pt-BR', {
              day: '2-digit',
              month: '2-digit',
              hour: '2-digit',
              minute: '2-digit',
            })}
          </Text>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16, backgroundColor: '#f9fafb' },
  title: { fontSize: 24, fontWeight: '700', marginBottom: 12 },
  summaryRow: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 12,
  },
  summaryStat: {
    flex: 1,
    backgroundColor: '#fff',
    padding: 10,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#e5e7eb',
    alignItems: 'center',
  },
  summaryValue: { fontSize: 22, fontWeight: '700' },
  summaryLabel: { fontSize: 11, color: '#6b7280', marginTop: 2, textTransform: 'uppercase' },
  tabs: { flexDirection: 'row', gap: 6, marginBottom: 12 },
  tabBtn: {
    flex: 1,
    padding: 8,
    borderRadius: 8,
    backgroundColor: '#e5e7eb',
    alignItems: 'center',
  },
  tabBtnActive: { backgroundColor: '#2563eb' },
  tabText: { color: '#374151', fontWeight: '600', fontSize: 13 },
  tabTextActive: { color: '#fff' },
  empty: { textAlign: 'center', marginTop: 32, color: '#6b7280' },
  groupCard: {
    backgroundColor: '#fff',
    padding: 12,
    borderRadius: 12,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  groupHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  groupLabel: { fontSize: 16, fontWeight: '700', flex: 1 },
  groupCount: { fontSize: 12, color: '#6b7280' },
  groupItem: {
    paddingVertical: 6,
    borderTopWidth: 1,
    borderTopColor: '#f3f4f6',
  },
  groupItemText: { fontSize: 14, color: '#111' },
  groupItemMeta: { fontSize: 12, color: '#6b7280', marginTop: 2 },
});
