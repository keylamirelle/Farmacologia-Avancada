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

type Nav = NativeStackNavigationProp<RootStackParamList, 'SchoolForm'>;
type Route = RouteProp<RootStackParamList, 'SchoolForm'>;

export function SchoolFormScreen() {
  const nav = useNavigation<Nav>();
  const route = useRoute<Route>();
  const id = route.params?.id;

  const [name, setName] = useState('');
  const [city, setCity] = useState('');
  const [active, setActive] = useState(true);
  const [loading, setLoading] = useState(!!id);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!id) return;
    supabase
      .from('schools')
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
          setCity(data.city ?? '');
          setActive(data.active);
        }
        setLoading(false);
      });
  }, [id, nav]);

  async function save() {
    if (!name.trim()) return Alert.alert('Informe o nome da escola');
    setSaving(true);
    const payload = {
      name: name.trim(),
      city: city.trim() || null,
      active,
    };
    const { error } = id
      ? await supabase.from('schools').update(payload).eq('id', id)
      : await supabase.from('schools').insert(payload);
    setSaving(false);
    if (error) return Alert.alert('Erro', error.message);
    nav.goBack();
  }

  async function remove() {
    if (!id) return;
    Alert.alert('Excluir escola', 'Continuar?', [
      { text: 'Cancelar', style: 'cancel' },
      {
        text: 'Excluir',
        style: 'destructive',
        onPress: async () => {
          const { error } = await supabase.from('schools').delete().eq('id', id);
          if (error) {
            Alert.alert(
              'Não foi possível excluir',
              'Provavelmente esta escola tem retiradas registradas. Marque como inativa em vez de excluir.'
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
      <TextInput style={styles.input} value={name} onChangeText={setName} placeholder="Ex: Escola Municipal X" />

      <Text style={styles.label}>Cidade (opcional)</Text>
      <TextInput style={styles.input} value={city} onChangeText={setCity} placeholder="Ex: Recife / PE" />

      <View style={styles.switchRow}>
        <View style={{ flex: 1 }}>
          <Text style={styles.switchLabel}>Ativa</Text>
          <Text style={styles.switchHelp}>Inativas não aparecem em novas retiradas</Text>
        </View>
        <Switch value={active} onValueChange={setActive} />
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
