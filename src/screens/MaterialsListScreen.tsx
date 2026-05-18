import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useMemo, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { MaterialSummaryCard } from '../components/MaterialSummaryCard';
import { useMaterialStatus } from '../hooks/useMaterials';
import type { RootStackParamList } from '../navigation/RootNavigator';

type Nav = NativeStackNavigationProp<RootStackParamList>;

export function MaterialsListScreen() {
  const nav = useNavigation<Nav>();
  const { items, loading, refresh } = useMaterialStatus();
  const [search, setSearch] = useState('');

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return items;
    return items.filter((m) => m.name.toLowerCase().includes(q));
  }, [items, search]);

  return (
    <View style={styles.container}>
      <View style={styles.headerRow}>
        <TextInput
          style={styles.search}
          placeholder="Buscar material"
          value={search}
          onChangeText={setSearch}
          autoCapitalize="none"
        />
        <Pressable style={styles.addBtn} onPress={() => nav.navigate('MaterialForm', {})}>
          <Text style={styles.addBtnText}>+ Novo</Text>
        </Pressable>
      </View>

      {loading && items.length === 0 ? (
        <ActivityIndicator style={{ marginTop: 24 }} />
      ) : (
        <FlatList
          data={filtered}
          keyExtractor={(m) => m.id}
          contentContainerStyle={{ padding: 16, paddingTop: 0 }}
          refreshControl={<RefreshControl refreshing={loading} onRefresh={refresh} />}
          renderItem={({ item }) => (
            <MaterialSummaryCard
              item={item}
              onPress={() => nav.navigate('MaterialForm', { id: item.id })}
            />
          )}
          ListEmptyComponent={
            <Text style={styles.empty}>
              Nenhum material cadastrado. Toque em &quot;+ Novo&quot;.
            </Text>
          }
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f9fafb' },
  headerRow: { flexDirection: 'row', alignItems: 'center', padding: 16, gap: 8 },
  search: {
    flex: 1,
    borderWidth: 1,
    borderColor: '#d1d5db',
    borderRadius: 8,
    padding: 10,
    backgroundColor: '#fff',
  },
  addBtn: {
    backgroundColor: '#2563eb',
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 8,
  },
  addBtnText: { color: '#fff', fontWeight: '600' },
  empty: { textAlign: 'center', marginTop: 32, color: '#6b7280' },
});
