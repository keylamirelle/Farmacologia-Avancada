import type { RouteProp } from '@react-navigation/native';
import { useNavigation, useRoute } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { useAuth } from '../context/AuthContext';
import { supabase } from '../lib/supabase';
import type { RootStackParamList } from '../navigation/RootNavigator';

type Nav = NativeStackNavigationProp<RootStackParamList, 'ProductForm'>;
type Route = RouteProp<RootStackParamList, 'ProductForm'>;

export function ProductFormScreen() {
  const nav = useNavigation<Nav>();
  const route = useRoute<Route>();
  const { userId } = useAuth();
  const editingId = route.params?.productId;

  const [name, setName] = useState('');
  const [sku, setSku] = useState('');
  const [unit, setUnit] = useState('un');
  const [minStock, setMinStock] = useState('0');
  const [loading, setLoading] = useState(!!editingId);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!editingId) return;
    supabase
      .from('products')
      .select('*')
      .eq('id', editingId)
      .single()
      .then(({ data, error }) => {
        if (error) {
          Alert.alert('Erro', error.message);
          nav.goBack();
          return;
        }
        if (data) {
          setName(data.name);
          setSku(data.sku ?? '');
          setUnit(data.unit);
          setMinStock(String(data.min_stock));
        }
        setLoading(false);
      });
  }, [editingId, nav]);

  async function save() {
    if (!name.trim()) {
      Alert.alert('Informe o nome do produto');
      return;
    }
    setSaving(true);
    try {
      const payload = {
        name: name.trim(),
        sku: sku.trim() || null,
        unit: unit.trim() || 'un',
        min_stock: Number(minStock) || 0,
      };
      if (editingId) {
        const { error } = await supabase.from('products').update(payload).eq('id', editingId);
        if (error) throw error;
      } else {
        const { error } = await supabase
          .from('products')
          .insert({ ...payload, created_by: userId });
        if (error) throw error;
      }
      nav.goBack();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Erro ao salvar';
      Alert.alert('Erro', message);
    } finally {
      setSaving(false);
    }
  }

  async function remove() {
    if (!editingId) return;
    Alert.alert('Excluir produto', 'Tem certeza? Esta acao nao pode ser desfeita.', [
      { text: 'Cancelar', style: 'cancel' },
      {
        text: 'Excluir',
        style: 'destructive',
        onPress: async () => {
          const { error } = await supabase.from('products').delete().eq('id', editingId);
          if (error) {
            Alert.alert('Erro', error.message);
          } else {
            nav.goBack();
          }
        },
      },
    ]);
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator />
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ padding: 16 }}>
      <Text style={styles.label}>Nome *</Text>
      <TextInput style={styles.input} value={name} onChangeText={setName} placeholder="Ex: Caneta azul" />

      <Text style={styles.label}>SKU (opcional)</Text>
      <TextInput
        style={styles.input}
        value={sku}
        onChangeText={setSku}
        autoCapitalize="characters"
        placeholder="Codigo unico"
      />

      <Text style={styles.label}>Unidade</Text>
      <TextInput
        style={styles.input}
        value={unit}
        onChangeText={setUnit}
        placeholder="un, kg, cx, l"
      />

      <Text style={styles.label}>Estoque minimo</Text>
      <TextInput
        style={styles.input}
        value={minStock}
        onChangeText={setMinStock}
        keyboardType="numeric"
      />

      <Pressable
        style={[styles.btn, { backgroundColor: '#2563eb' }, saving && { opacity: 0.6 }]}
        onPress={save}
        disabled={saving}
      >
        <Text style={styles.btnText}>{saving ? 'Salvando...' : 'Salvar'}</Text>
      </Pressable>

      {editingId && (
        <Pressable
          style={[styles.btn, { backgroundColor: '#b91c1c', marginTop: 12 }]}
          onPress={remove}
        >
          <Text style={styles.btnText}>Excluir produto</Text>
        </Pressable>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f9fafb' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  label: { marginTop: 8, marginBottom: 4, color: '#374151', fontWeight: '500' },
  input: {
    borderWidth: 1,
    borderColor: '#d1d5db',
    borderRadius: 8,
    padding: 12,
    backgroundColor: '#fff',
    fontSize: 16,
  },
  btn: { padding: 14, borderRadius: 8, alignItems: 'center', marginTop: 24 },
  btnText: { color: '#fff', fontWeight: '600', fontSize: 16 },
});
