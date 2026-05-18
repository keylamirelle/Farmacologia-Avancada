import { Pressable, StyleSheet, Text, View } from 'react-native';
import type { WithdrawalWithJoins } from '../lib/types';

function formatDateTime(iso: string) {
  const d = new Date(iso);
  return d.toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function WithdrawalCard({
  withdrawal,
  onReturnPress,
}: {
  withdrawal: WithdrawalWithJoins;
  onReturnPress?: () => void;
}) {
  const isActive = withdrawal.returned_at === null;
  const isReturnable = withdrawal.materials?.returnable ?? true;
  const status = !isActive ? 'devolvido' : isReturnable ? 'em uso' : 'consumido';

  const statusColor = !isActive ? '#475569' : isReturnable ? '#b45309' : '#7c3aed';
  const statusBg = !isActive ? '#f1f5f9' : isReturnable ? '#fef3c7' : '#ede9fe';

  return (
    <View style={styles.card}>
      <View style={styles.header}>
        <Text style={styles.material} numberOfLines={1}>
          {withdrawal.materials?.name ?? '(material removido)'}
        </Text>
        <Text style={styles.qty}>
          {withdrawal.quantity} {withdrawal.materials?.unit ?? ''}
        </Text>
      </View>

      <View style={styles.row}>
        <Text style={styles.label}>Quem:</Text>
        <Text style={styles.value}>{withdrawal.people?.name ?? '(removido)'}</Text>
      </View>
      <View style={styles.row}>
        <Text style={styles.label}>Escola:</Text>
        <Text style={styles.value}>{withdrawal.schools?.name ?? '(removida)'}</Text>
      </View>
      <View style={styles.row}>
        <Text style={styles.label}>Retirado:</Text>
        <Text style={styles.value}>{formatDateTime(withdrawal.withdrawn_at)}</Text>
      </View>
      {withdrawal.returned_at && (
        <View style={styles.row}>
          <Text style={styles.label}>Devolvido:</Text>
          <Text style={styles.value}>{formatDateTime(withdrawal.returned_at)}</Text>
        </View>
      )}
      {withdrawal.note ? (
        <Text style={styles.note}>{withdrawal.note}</Text>
      ) : null}

      <View style={styles.footer}>
        <View style={[styles.badge, { backgroundColor: statusBg }]}>
          <Text style={[styles.badgeText, { color: statusColor }]}>{status}</Text>
        </View>
        {isActive && isReturnable && onReturnPress && (
          <Pressable style={styles.returnBtn} onPress={onReturnPress}>
            <Text style={styles.returnBtnText}>Marcar devolvido</Text>
          </Pressable>
        )}
      </View>
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
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  material: { fontSize: 16, fontWeight: '700', flex: 1 },
  qty: { fontSize: 16, fontWeight: '700', color: '#b45309', marginLeft: 8 },
  row: { flexDirection: 'row', marginTop: 2 },
  label: { width: 72, color: '#6b7280', fontSize: 13 },
  value: { flex: 1, fontSize: 13, color: '#111' },
  note: { marginTop: 6, fontStyle: 'italic', color: '#374151', fontSize: 13 },
  footer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: 10,
  },
  badge: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12 },
  badgeText: { fontSize: 12, fontWeight: '600' },
  returnBtn: {
    backgroundColor: '#15803d',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
  },
  returnBtnText: { color: '#fff', fontWeight: '600', fontSize: 13 },
});
