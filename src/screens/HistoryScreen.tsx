import { ActivityIndicator, FlatList, RefreshControl, StyleSheet, Text, View } from 'react-native';
import { MovementRow } from '../components/MovementRow';
import { useTodayMovements } from '../hooks/useMovements';

export function HistoryScreen() {
  const { movements, loading, refresh } = useTodayMovements();

  const todayLabel = new Date().toLocaleDateString('pt-BR', {
    weekday: 'long',
    day: '2-digit',
    month: 'long',
  });

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Movimentacoes de hoje</Text>
      <Text style={styles.subtitle}>{todayLabel}</Text>

      {loading && movements.length === 0 ? (
        <ActivityIndicator style={{ marginTop: 24 }} />
      ) : (
        <FlatList
          data={movements}
          keyExtractor={(m) => m.id}
          contentContainerStyle={{ paddingBottom: 24 }}
          refreshControl={<RefreshControl refreshing={loading} onRefresh={refresh} />}
          renderItem={({ item }) => <MovementRow movement={item} />}
          ListEmptyComponent={
            <Text style={styles.empty}>Nenhuma movimentacao registrada hoje.</Text>
          }
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16, backgroundColor: '#f9fafb' },
  title: { fontSize: 22, fontWeight: '700' },
  subtitle: { color: '#6b7280', marginBottom: 12, textTransform: 'capitalize' },
  empty: { textAlign: 'center', marginTop: 32, color: '#6b7280' },
});
