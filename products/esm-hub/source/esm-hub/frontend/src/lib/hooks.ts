import { useQuery } from '@tanstack/react-query';
import { api, asList } from './api';
import type { Member, Priority, Reference } from './types';

export function useReference() {
  return useQuery({ queryKey: ['reference'], queryFn: () => api<Reference>('/reference'), staleTime: 5 * 60_000 });
}

export function usePriorities() {
  return useQuery({ queryKey: ['priorities'], queryFn: () => api<Priority[]>('/incidents/meta/priorities'), staleTime: 5 * 60_000 });
}

export function useTeamMembers(teamId?: number | string) {
  return useQuery({
    queryKey: ['team-members', teamId],
    enabled: !!teamId,
    queryFn: async () => asList(await api<Member[] | { items: Member[] }>(`/teams/${teamId}/members`)),
  });
}

export function useNames() {
  const ref = useReference();
  return {
    team: (id?: number | null) => ref.data?.teams.find((t) => t.teamId === id)?.name ?? (id ? `Team ${id}` : '-'),
    service: (id?: number | null) => ref.data?.services.find((s) => s.serviceId === id)?.name ?? (id ? `Service ${id}` : '-'),
    office: (id?: number | null) => ref.data?.offices.find((s) => s.officeId === id)?.name ?? (id ? `Office ${id}` : '-'),
  };
}
