import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useMemo, useState } from 'react';
import {
  Alert,
  FlatList,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { QuantityInput } from '../components/QuantityInput';
import { useMaterialStatus } from '../hooks/useMaterials';
import { usePeople } from '../hooks/usePeople';
import { useSchools } from '../hooks/useSchools';
import { supabase } from '../lib/supabase';
import type { MaterialStatus, Person, School } from '../lib/types';
import type { RootStackParamList } from '../navigation/RootNavigator';

type Nav = NativeStackNavigationProp<RootStackParamList>;

export function NewWithdrawalScreen() {
  const nav = useNavigation<Nav>();
  const { people } = usePeople({ activeOnly: true });
  const { schools } = useSchools({ activeOnly: true });
  const { items: materials } = useMaterialStatus();

  const [person, setPerson] = useState<Person | null>(null);
  const [school, setSchool] = useState<School | null>(null);
  const [material, setMaterial] = useState<MaterialStatus | null>(null);
  const [quantity, setQuantity] = useState('1');
  const [note, setNote] = useState('');
  const [picker, setPicker] = useState<'person' | 'school' | 'material' | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const available = material ? Math.max(0, Number(material.available)) : 0;

  async function submit() {
    if (!person) return Alert.alert('Selecione o responsável');
    if (!school) return Alert.alert('Selecione a escola');
    if (!material) return Alert.alert('Selecione o material');
    const qty = Number(quantity);
    if (!qty || qty <= 0) return Alert.alert('Quantidade inválida');
    if (qty > available) {
      return Alert.alert(
        'Quantidade indisponível',
        `Apenas ${available} ${material.unit} disponível.`
      );
    }
    setSubmitting(true);
    const { error } = await supabase.from('withdrawals').insert({
      person_id: person.id,
      school_id: school.id,
      material_id: material.id,
      quantity: qty,
      note: note.trim() || null,
    });
    setSubmitting(false);
    if (error) {
      Alert.alert('Erro', error.message);
      return;
    }
    nav.goBack();
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ padding: 16 }}>
      <Text style={styles.label}>Responsável</Text>
      <SelectorButton
        placeholder="Toque para escolher uma pessoa"
        value={person?.name ?? null}
        onPress={() => setPicker('person')}
      />
      {person?.role ? <Text style={styles.helper}>{person.role}</Text> : null}

      <Text style={styles.label}>Escola</Text>
      <SelectorButton
        placeholder="Toque para escolher uma escola"
        value={school?.name ?? null}
        onPress={() => setPicker('school')}
      />
      {school?.city ? <Text style={styles.helper}>{school.city}</Text> : null}

      <Text style={styles.label}>Material</Text>
      <SelectorButton
        placeholder="Toque para escolher um material"
        value={material?.name ?? null}
        onPress={() => setPicker('material')}
      />
      {material ? (
        <Text style={styles.helper}>
          Disponível: {available} {material.unit}
          {!material.returnable ? ' · consumível (não volta)' : ''}
        </Text>
      ) : null}

      <View style={{ marginTop: 8 }}>
        <QuantityInput
          label="Quantidade"
          value={quantity}
          onChangeText={setQuantity}
          placeholder="0"
        />
      </View>

      <Text style={styles.label}>Observação (opcional)</Text>
      <TextInput
        style={[styles.input, { minHeight: 60 }]}
        value={note}
        onChangeText={setNote}
        multiline
        placeholder="Ex: aula de ciências, sala 3"
      />

      <Pressable
        style={[styles.submit, submitting && { opacity: 0.6 }]}
        onPress={submit}
        disabled={submitting}
      >
        <Text style={styles.submitText}>
          {submitting ? 'Registrando...' : 'Registrar retirada'}
        </Text>
      </Pressable>

      <PickerModal
        visible={picker !== null}
        onClose={() => setPicker(null)}
        title={
          picker === 'person'
            ? 'Selecionar responsável'
            : picker === 'school'
            ? 'Selecionar escola'
            : 'Selecionar material'
        }
        items={
          picker === 'person'
            ? people.map((p) => ({
                key: p.id,
                label: p.name,
                sub: p.role ?? undefined,
                disabled: false,
              }))
            : picker === 'school'
            ? schools.map((s) => ({
                key: s.id,
                label: s.name,
                sub: s.city ?? undefined,
                disabled: false,
              }))
            : materials.map((m) => {
                const avail = Math.max(0, Number(m.available));
                return {
                  key: m.id,
                  label: m.name,
                  sub: `${avail} ${m.unit} disponível${
                    !m.returnable ? ' · consumível' : ''
                  }`,
                  disabled: avail <= 0,
                };
              })
        }
        onSelect={(key) => {
          if (picker === 'person') setPerson(people.find((p) => p.id === key) ?? null);
          else if (picker === 'school') setSchool(schools.find((s) => s.id === key) ?? null);
          else setMaterial(materials.find((m) => m.id === key) ?? null);
          setPicker(null);
        }}
        emptyHint={
          picker === 'person'
            ? 'Nenhuma pessoa cadastrada. Vá em Cadastros > Pessoas.'
            : picker === 'school'
            ? 'Nenhuma escola cadastrada. Vá em Cadastros > Escolas.'
            : 'Nenhum material cadastrado. Vá em Cadastros > Materiais.'
        }
      />
    </ScrollView>
  );
}

function SelectorButton({
  placeholder,
  value,
  onPress,
}: {
  placeholder: string;
  value: string | null;
  onPress: () => void;
}) {
  return (
    <Pressable style={styles.selector} onPress={onPress}>
      <Text style={value ? styles.selectorValue : styles.selectorPlaceholder}>
        {value ?? placeholder}
      </Text>
      <Text style={styles.selectorChevron}>›</Text>
    </Pressable>
  );
}

type PickerItem = { key: string; label: string; sub?: string; disabled: boolean };

function PickerModal({
  visible,
  onClose,
  title,
  items,
  onSelect,
  emptyHint,
}: {
  visible: boolean;
  onClose: () => void;
  title: string;
  items: PickerItem[];
  onSelect: (key: string) => void;
  emptyHint: string;
}) {
  const [search, setSearch] = useState('');
  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return items;
    return items.filter((i) => i.label.toLowerCase().includes(q));
  }, [items, search]);

  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <View style={modalStyles.container}>
        <View style={modalStyles.header}>
          <Text style={modalStyles.title}>{title}</Text>
          <Pressable onPress={onClose}>
            <Text style={modalStyles.close}>Fechar</Text>
          </Pressable>
        </View>
        <TextInput
          style={modalStyles.search}
          placeholder="Buscar..."
          value={search}
          onChangeText={setSearch}
          autoCapitalize="none"
        />
        <FlatList
          data={filtered}
          keyExtractor={(i) => i.key}
          contentContainerStyle={{ padding: 12 }}
          renderItem={({ item }) => (
            <Pressable
              onPress={() => !item.disabled && onSelect(item.key)}
              style={[modalStyles.item, item.disabled && modalStyles.itemDisabled]}
            >
              <Text style={modalStyles.itemLabel}>{item.label}</Text>
              {item.sub ? <Text style={modalStyles.itemSub}>{item.sub}</Text> : null}
            </Pressable>
          )}
          ListEmptyComponent={
            <Text style={modalStyles.empty}>{items.length === 0 ? emptyHint : 'Nenhum resultado.'}</Text>
          }
        />
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f9fafb' },
  label: { marginTop: 12, marginBottom: 6, color: '#374151', fontWeight: '500' },
  helper: { fontSize: 12, color: '#6b7280', marginTop: 4 },
  selector: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    padding: 14,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#d1d5db',
  },
  selectorValue: { fontSize: 16, color: '#111', flex: 1 },
  selectorPlaceholder: { fontSize: 16, color: '#9ca3af', flex: 1 },
  selectorChevron: { fontSize: 22, color: '#9ca3af' },
  input: {
    borderWidth: 1,
    borderColor: '#d1d5db',
    borderRadius: 8,
    padding: 12,
    backgroundColor: '#fff',
    fontSize: 16,
  },
  submit: {
    backgroundColor: '#15803d',
    padding: 14,
    borderRadius: 8,
    alignItems: 'center',
    marginTop: 24,
  },
  submitText: { color: '#fff', fontWeight: '700', fontSize: 16 },
});

const modalStyles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#e5e7eb',
  },
  title: { fontSize: 18, fontWeight: '700' },
  close: { color: '#2563eb', fontWeight: '600' },
  search: {
    margin: 12,
    padding: 10,
    borderWidth: 1,
    borderColor: '#d1d5db',
    borderRadius: 8,
  },
  item: {
    padding: 12,
    borderRadius: 8,
    backgroundColor: '#f9fafb',
    marginBottom: 8,
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  itemDisabled: { opacity: 0.5 },
  itemLabel: { fontSize: 15, fontWeight: '500' },
  itemSub: { fontSize: 12, color: '#6b7280', marginTop: 2 },
  empty: { textAlign: 'center', color: '#6b7280', marginTop: 32 },
});
