import type { RouteProp } from '@react-navigation/native';
import { useNavigation, useRoute } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useMemo, useState } from 'react';
import {
  Alert,
  FlatList,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { QuantityInput } from '../components/QuantityInput';
import { useAuth } from '../context/AuthContext';
import { useProducts } from '../hooks/useProducts';
import { supabase } from '../lib/supabase';
import type { MovementType, Product } from '../lib/types';
import type { RootStackParamList } from '../navigation/RootNavigator';

type Nav = NativeStackNavigationProp<RootStackParamList>;
type Route = RouteProp<RootStackParamList, 'Entry' | 'Withdrawal'>;

export function MovementForm({ type }: { type: MovementType }) {
  const nav = useNavigation<Nav>();
  const route = useRoute<Route>();
  const { userId } = useAuth();
  const { products } = useProducts();

  const initialId = route.params?.productId;
  const [productId, setProductId] = useState<string | null>(initialId ?? null);
  const [quantity, setQuantity] = useState('1');
  const [note, setNote] = useState('');
  const [search, setSearch] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const selected = useMemo<Product | null>(
    () => products.find((p) => p.id === productId) ?? null,
    [products, productId]
  );

  const filteredProducts = useMemo(() => {
    if (productId) return [];
    const q = search.trim().toLowerCase();
    const base = q
      ? products.filter((p) => p.name.toLowerCase().includes(q))
      : products;
    return base.slice(0, 20);
  }, [products, search, productId]);

  async function submit() {
    if (!selected) {
      Alert.alert('Selecione um produto');
      return;
    }
    const qty = Number(quantity);
    if (!qty || qty <= 0) {
      Alert.alert('Quantidade invalida');
      return;
    }
    if (type === 'withdrawal' && qty > selected.current_stock) {
      Alert.alert(
        'Estoque insuficiente',
        `Estoque atual: ${selected.current_stock} ${selected.unit}.`
      );
      return;
    }
    setSubmitting(true);
    const { error } = await supabase.from('stock_movements').insert({
      product_id: selected.id,
      type,
      quantity: qty,
      note: note.trim() || null,
      performed_by: userId,
    });
    setSubmitting(false);
    if (error) {
      Alert.alert('Erro', error.message);
      return;
    }
    nav.goBack();
  }

  const isEntry = type === 'entry';
  const color = isEntry ? '#15803d' : '#b91c1c';

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ padding: 16 }}>
      <Text style={styles.heading}>{isEntry ? 'Entrada de estoque' : 'Retirada de estoque'}</Text>

      {selected ? (
        <View style={styles.selectedBox}>
          <Text style={styles.selectedName}>{selected.name}</Text>
          <Text style={styles.selectedMeta}>
            Estoque atual: {selected.current_stock} {selected.unit}
          </Text>
          <Pressable onPress={() => setProductId(null)}>
            <Text style={styles.changeLink}>Trocar produto</Text>
          </Pressable>
        </View>
      ) : (
        <View style={{ marginBottom: 12 }}>
          <Text style={styles.label}>Selecione o produto</Text>
          <TextInput
            style={styles.input}
            placeholder="Buscar produto..."
            value={search}
            onChangeText={setSearch}
            autoCapitalize="none"
          />
          <FlatList
            data={filteredProducts}
            keyExtractor={(p) => p.id}
            scrollEnabled={false}
            renderItem={({ item }) => (
              <Pressable style={styles.productOption} onPress={() => setProductId(item.id)}>
                <Text style={styles.productOptionName}>{item.name}</Text>
                <Text style={styles.productOptionMeta}>
                  {item.current_stock} {item.unit}
                </Text>
              </Pressable>
            )}
            ListEmptyComponent={
              <Text style={styles.empty}>Nenhum produto encontrado.</Text>
            }
          />
        </View>
      )}

      <QuantityInput
        label="Quantidade"
        value={quantity}
        onChangeText={setQuantity}
        placeholder="0"
      />

      <Text style={styles.label}>Nota (opcional)</Text>
      <TextInput
        style={[styles.input, { minHeight: 60 }]}
        value={note}
        onChangeText={setNote}
        placeholder={isEntry ? 'Ex: chegada de fornecedor' : 'Ex: uso interno'}
        multiline
      />

      <Pressable
        style={[styles.btn, { backgroundColor: color }, submitting && { opacity: 0.6 }]}
        onPress={submit}
        disabled={submitting}
      >
        <Text style={styles.btnText}>
          {submitting ? 'Registrando...' : isEntry ? 'Registrar entrada' : 'Registrar retirada'}
        </Text>
      </Pressable>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f9fafb' },
  heading: { fontSize: 20, fontWeight: '700', marginBottom: 12 },
  label: { marginTop: 8, marginBottom: 6, color: '#374151', fontWeight: '500' },
  input: {
    borderWidth: 1,
    borderColor: '#d1d5db',
    borderRadius: 8,
    padding: 12,
    backgroundColor: '#fff',
    fontSize: 16,
  },
  selectedBox: {
    backgroundColor: '#eff6ff',
    borderColor: '#bfdbfe',
    borderWidth: 1,
    padding: 12,
    borderRadius: 8,
    marginBottom: 12,
  },
  selectedName: { fontSize: 16, fontWeight: '600' },
  selectedMeta: { marginTop: 2, color: '#374151' },
  changeLink: { color: '#2563eb', marginTop: 8 },
  productOption: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 10,
    paddingHorizontal: 12,
    backgroundColor: '#fff',
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#e5e7eb',
    marginTop: 6,
  },
  productOptionName: { fontWeight: '500' },
  productOptionMeta: { color: '#6b7280' },
  empty: { color: '#6b7280', marginTop: 8, fontStyle: 'italic' },
  btn: { padding: 14, borderRadius: 8, alignItems: 'center', marginTop: 24 },
  btnText: { color: '#fff', fontWeight: '600', fontSize: 16 },
});
