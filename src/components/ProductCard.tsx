import { Pressable, StyleSheet, Text, View } from 'react-native';
import type { Product } from '../lib/types';

export function ProductCard({
  product,
  onPress,
}: {
  product: Product;
  onPress?: () => void;
}) {
  const low = product.current_stock <= product.min_stock;
  return (
    <Pressable
      style={({ pressed }) => [styles.card, pressed && styles.pressed]}
      onPress={onPress}
    >
      <View style={styles.row}>
        <Text style={styles.name}>{product.name}</Text>
        {low && (
          <View style={styles.badge}>
            <Text style={styles.badgeText}>estoque baixo</Text>
          </View>
        )}
      </View>
      {product.sku ? <Text style={styles.sku}>SKU: {product.sku}</Text> : null}
      <Text style={styles.stock}>
        {product.current_stock} {product.unit} (minimo {product.min_stock})
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#fff',
    padding: 14,
    borderRadius: 10,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  pressed: { opacity: 0.7 },
  row: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  name: { fontSize: 16, fontWeight: '600', flexShrink: 1 },
  sku: { color: '#6b7280', marginTop: 4, fontSize: 12 },
  stock: { marginTop: 6, fontSize: 14, color: '#111' },
  badge: {
    backgroundColor: '#fee2e2',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 12,
    marginLeft: 8,
  },
  badgeText: { color: '#991b1b', fontSize: 11, fontWeight: '600' },
});
