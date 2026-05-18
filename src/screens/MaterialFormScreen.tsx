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
  Switch,
  Text,
  TextInput,
  View,
} from 'react-native';
import { supabase } from '../lib/supabase';
import type { RootStackParamList } from '../navigation/RootNavigator';

type Nav = NativeStackNavigationProp<RootStackParamList, 'MaterialForm'>;
type Route = RouteProp<RootStackParamList, 'MaterialForm'>;

export function MaterialFormScreen() {
  const nav = useNavigation<Nav>();
  const route = useRoute<Route>();
  const id = route.params?.id;

  const [name, setName] = useState('');
  const [unit, setUnit] = useState('un');
  const [totalQuantity, setTotalQuantity] = useState('0');
  const [returnable, setReturnable] = useState(true);
  const [loading, setLoading] = useState(!!id);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!id) return;
    supabase
      .from('materials')
      .select('*')
      .eq('id', id)
      .single()
      .then(({ data, error }) => {
        if (error) {
          Alert.alert('Erro', error.message);
          nav.goBack();
          return;
        }
        if (data) {
          setName(data.name);
          setUnit(data.unit);
          setTotalQuantity(String(data.total_quantity));
          setReturnable(data.returnable);
        }
        setLoading(false);
      });
  }, [id, nav]);

  async function save() {
    if (!name.trim()) return Alert.alert('Informe o nome do material');
    const total = Number(totalQuantity);
    if (isNaN(total) || total < 0) return Alert.alert('Quantidade total inválida');

    setSaving(true);
    const payload = {
      name: name.trim(),
      unit: unit.trim() || 'un',
      total_quantity: total,
      returnable,
    };
    const { error } = id
      ? await supabase.from('materials').update(payload).eq('id', id)
      : await supabase.from('materials').insert(payload);
    setSaving(false);
    if (error) return Alert.alert('Erro', error.message);
    nav.goBack();
  }

  async function remove() {
    if (!id) return;
    Alert.alert('Excluir material', 'Continuar?', [
      { text: 'Cancelar', style: 'cancel' },
      {
        text: 'Excluir',
        style: 'destructive',
        onPress: async () => {
          const { error } = await supabase.from('materials').delete().eq('id', id);
          if (error) {
            Alert.alert(
              'Não foi possível excluir',
              'Provavelmente existem retiradas deste material. Você pode zerar a quantidade total.'
            );
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
      <TextInput
        style={styles.input}
        value={name}
        onChangeText={setName}
        placeholder="Ex: Microscópio óptico"
      />

      <Text style={styles.label}>Unidade</Text>
      <TextInput
        style={styles.input}
        value={unit}
        onChangeText={setUnit}
        placeholder="un, kg, cx, l, pacote"
      />

      <Text style={styles.label}>Quantidade total disponível *</Text>
      <TextInput
        style={styles.input}
        value={totalQuantity}
        onChangeText={setTotalQuantity}
        keyboardType="numeric"
      />
      <Text style={styles.helper}>
        Quantos exemplares deste material você tem no total (incluindo os que estão em uso).
      </Text>

      <View style={styles.switchRow}>
        <View style={{ flex: 1 }}>
          <Text style={styles.switchLabel}>
            {returnable ? 'Retorna após uso (empréstimo)' : 'Consumível (não retorna)'}
          </Text>
          <Text style={styles.switchHelp}>
            {returnable
              ? 'Ex: jogos, livros, equipamentos — o material volta ao estoque depois.'
              : 'Ex: papel, lapiseira — quando sai, sai de vez (diminui o disponível para sempre).'}
          </Text>
        </View>
        <Switch value={returnable} onValueChange={setReturnable} />
      </View>

      <Pressable
        style={[styles.btn, { backgroundColor: '#2563eb' }, saving && { opacity: 0.6 }]}
        onPress={save}
        disabled={saving}
      >
        <Text style={styles.btnText}>{saving ? 'Salvando...' : 'Salvar'}</Text>
      </Pressable>

      {id && (
        <Pressable
          style={[styles.btn, { backgroundColor: '#b91c1c', marginTop: 12 }]}
          onPress={remove}
        >
          <Text style={styles.btnText}>Excluir</Text>
        </Pressable>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f9fafb' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  label: { marginTop: 12, marginBottom: 6, color: '#374151', fontWeight: '500' },
  input: {
    borderWidth: 1,
    borderColor: '#d1d5db',
    borderRadius: 8,
    padding: 12,
    backgroundColor: '#fff',
    fontSize: 16,
  },
  helper: { fontSize: 12, color: '#6b7280', marginTop: 4 },
  switchRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 16,
    padding: 12,
    backgroundColor: '#fff',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  switchLabel: { fontWeight: '500', fontSize: 15 },
  switchHelp: { fontSize: 12, color: '#6b7280', marginTop: 2 },
  btn: { padding: 14, borderRadius: 8, alignItems: 'center', marginTop: 24 },
  btnText: { color: '#fff', fontWeight: '700', fontSize: 16 },
});
