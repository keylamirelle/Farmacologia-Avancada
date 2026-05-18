import { Pressable, StyleSheet, Text, View } from 'react-native';
import type { MaterialStatus } from '../lib/types';

export function MaterialSummaryCard({
  item,
  onPress,
}: {
  item: MaterialStatus;
  onPress?: () => void;
}) {
  const available = Math.max(0, Number(item.available));
  const inUse = Number(item.in_use);
  const total = Number(item.total_quantity);
  const low = available <= 0;

  return (
    <Pressable
      style={({ pressed }) => [styles.card, pressed && styles.pressed]}
      onPress={onPress}
    >
      <View style={styles.header}>
        <Text style={styles.name} numberOfLines={1}>
          {item.name}
        </Text>
        {!item.returnable && (
          <View style={styles.tagConsumable}>
            <Text style={styles.tagText}>consumivel</Text>
          </View>
        )}
        {low && (
          <View style={styles.tagOut}>
            <Text style={styles.tagText}>zerado</Text>
          </View>
        )}
      </View>

      <View style={styles.stats}>
        <Stat label="Total" value={total} unit={item.unit} color="#111" />
        <Stat label="Em uso" value={inUse} unit={item.unit} color="#b45309" />
        <Stat label="Disponivel" value={available} unit={item.unit} color="#15803d" />
      </View>
    </Pressable>
  );
}

function Stat({
  label,
  value,
  unit,
  color,
}: {
  label: string;
  value: number;
  unit: string;
  color: string;
}) {
  return (
    <View style={styles.stat}>
      <Text style={styles.statLabel}>{label}</Text>
      <Text style={[styles.statValue, { color }]}>
        {value} <Text style={styles.statUnit}>{unit}</Text>
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#fff',
    padding: 14,
    borderRadius: 12,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  pressed: { opacity: 0.7 },
  header: { flexDirection: 'row', alignItems: 'center', marginBottom: 10 },
  name: { fontSize: 16, fontWeight: '700', flex: 1 },
  tagConsumable: {
    backgroundColor: '#e0e7ff',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 12,
    marginLeft: 6,
  },
  tagOut: {
    backgroundColor: '#fee2e2',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 12,
    marginLeft: 6,
  },
  tagText: { fontSize: 11, fontWeight: '600', color: '#1e293b' },
  stats: { flexDirection: 'row', justifyContent: 'space-between' },
  stat: { flex: 1 },
  statLabel: { fontSize: 11, color: '#6b7280', textTransform: 'uppercase' },
  statValue: { fontSize: 18, fontWeight: '700', marginTop: 2 },
  statUnit: { fontSize: 12, color: '#6b7280', fontWeight: '500' },
});
