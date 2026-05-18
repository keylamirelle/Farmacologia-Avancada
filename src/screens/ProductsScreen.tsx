import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useMemo, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  FlatList,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { ProductCard } from '../components/ProductCard';
import { useAuth } from '../context/AuthContext';
import { useProducts } from '../hooks/useProducts';
import type { RootStackParamList } from '../navigation/RootNavigator';

type Nav = NativeStackNavigationProp<RootStackParamList>;

export function ProductsScreen() {
  const nav = useNavigation<Nav>();
  const { products, loading, refresh } = useProducts();
  const { signOut } = useAuth();
  const [search, setSearch] = useState('');

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return products;
    return products.filter(
      (p) =>
        p.name.toLowerCase().includes(q) ||
        (p.sku ? p.sku.toLowerCase().includes(q) : false)
    );
  }, [products, search]);

  const lowStockCount = products.filter((p) => p.current_stock <= p.min_stock).length;

  function confirmSignOut() {
    Alert.alert('Sair', 'Deseja sair da conta?', [
      { text: 'Cancelar', style: 'cancel' },
      { text: 'Sair', style: 'destructive', onPress: () => signOut() },
    ]);
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <View style={{ flex: 1 }}>
          <Text style={styles.title}>Produtos</Text>
          {lowStockCount > 0 && (
            <Text style={styles.lowStockHint}>
              {lowStockCount} item(s) com estoque baixo
            </Text>
          )}
        </View>
        <Pressable onPress={confirmSignOut} style={styles.signOutBtn}>
          <Text style={styles.signOutText}>Sair</Text>
        </Pressable>
      </View>

      <TextInput
        style={styles.search}
        placeholder="Buscar por nome ou SKU"
        value={search}
        onChangeText={setSearch}
        autoCapitalize="none"
      />

      <View style={styles.actions}>
        <Pressable
          style={[styles.actionBtn, { backgroundColor: '#2563eb' }]}
          onPress={() => nav.navigate('ProductForm', {})}
        >
          <Text style={styles.actionText}>+ Novo produto</Text>
        </Pressable>
        <Pressable
          style={[styles.actionBtn, { backgroundColor: '#15803d' }]}
          onPress={() => nav.navigate('Entry', {})}
        >
          <Text style={styles.actionText}>Entrada</Text>
        </Pressable>
        <Pressable
          style={[styles.actionBtn, { backgroundColor: '#b91c1c' }]}
          onPress={() => nav.navigate('Withdrawal', {})}
        >
          <Text style={styles.actionText}>Retirada</Text>
        </Pressable>
      </View>

      {loading && products.length === 0 ? (
        <ActivityIndicator style={{ marginTop: 24 }} />
      ) : (
        <FlatList
          data={filtered}
          keyExtractor={(item) => item.id}
          contentContainerStyle={{ paddingBottom: 24 }}
          refreshControl={<RefreshControl refreshing={loading} onRefresh={refresh} />}
          renderItem={({ item }) => (
            <ProductCard
              product={item}
              onPress={() => nav.navigate('ProductForm', { productId: item.id })}
            />
          )}
          ListEmptyComponent={
            <Text style={styles.empty}>
              Nenhum produto ainda. Toque em &quot;Novo produto&quot; para comecar.
            </Text>
          }
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16, backgroundColor: '#f9fafb' },
  header: { flexDirection: 'row', alignItems: 'center', marginBottom: 12 },
  title: { fontSize: 24, fontWeight: '700' },
  lowStockHint: { color: '#b91c1c', marginTop: 2, fontSize: 12 },
  signOutBtn: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 6, backgroundColor: '#e5e7eb' },
  signOutText: { color: '#111', fontWeight: '500' },
  search: {
    borderWidth: 1,
    borderColor: '#d1d5db',
    borderRadius: 8,
    padding: 10,
    backgroundColor: '#fff',
    marginBottom: 12,
  },
  actions: { flexDirection: 'row', gap: 8, marginBottom: 14 },
  actionBtn: { flex: 1, padding: 10, borderRadius: 8, alignItems: 'center' },
  actionText: { color: '#fff', fontWeight: '600', fontSize: 13 },
  empty: { textAlign: 'center', marginTop: 32, color: '#6b7280' },
});
