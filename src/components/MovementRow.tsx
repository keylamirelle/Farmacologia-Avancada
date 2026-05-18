import { StyleSheet, Text, View } from 'react-native';
import type { MovementWithJoins } from '../lib/types';

export function MovementRow({ movement }: { movement: MovementWithJoins }) {
  const isEntry = movement.type === 'entry';
  const sign = isEntry ? '+' : '-';
  const color = isEntry ? '#15803d' : '#b91c1c';
  const time = new Date(movement.performed_at).toLocaleTimeString('pt-BR', {
    hour: '2-digit',
    minute: '2-digit',
  });
  const productName = movement.products?.name ?? '(produto removido)';
  const unit = movement.products?.unit ?? '';
  const who = movement.profiles?.display_name ?? 'desconhecido';

  return (
    <View style={styles.row}>
      <View style={styles.left}>
        <Text style={styles.product}>{productName}</Text>
        <Text style={styles.meta}>
          {time} · por {who}
        </Text>
        {movement.note ? <Text style={styles.note}>{movement.note}</Text> : null}
      </View>
      <Text style={[styles.qty, { color }]}>
        {sign}
        {movement.quantity} {unit}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    paddingVertical: 12,
    paddingHorizontal: 14,
    backgroundColor: '#fff',
    borderRadius: 10,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: '#e5e7eb',
    alignItems: 'center',
  },
  left: { flex: 1 },
  product: { fontSize: 15, fontWeight: '600' },
  meta: { fontSize: 12, color: '#6b7280', marginTop: 2 },
  note: { fontSize: 12, color: '#374151', marginTop: 4, fontStyle: 'italic' },
  qty: { fontSize: 18, fontWeight: '700', marginLeft: 12 },
});
