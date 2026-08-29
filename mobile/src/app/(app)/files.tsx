/**
 * Files: upload from the device, list, download, delete.
 *
 * Two pickers rather than one. A file picker on iOS shows the Files app,
 * which is not where anyone's photos are -- and photos are what people
 * actually want to attach from a phone. Offering both is the difference
 * between a feature that works and one that technically works.
 */

import * as DocumentPicker from 'expo-document-picker';
import { Directory, File, Paths } from 'expo-file-system';
import * as ImagePicker from 'expo-image-picker';
import * as Sharing from 'expo-sharing';
import { useCallback, useState } from 'react';
import { View } from 'react-native';
import { ActivityIndicator, Button, IconButton, List, useTheme } from 'react-native-paper';

import type { Attachment } from '@app/shared/types';

import { EmptyState, Screen, ScreenHeader } from '../../components/Screen';
import { ApiError, apiData } from '../../lib/api';
import { flags } from '../../lib/config';
import { routes } from '../../lib/routes';
import { currentTokens } from '../../lib/tokenStore';
import { useResource } from '../../lib/useResource';
import { useToast } from '../../store/toast';
import type { AppTheme } from '../../theme/paper';

/** What the backend's multipart handler needs for one file. */
interface PickedFile {
  uri: string;
  name: string;
  mimeType: string;
}

function humanSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function FilesScreen() {
  const theme = useTheme<AppTheme>();
  const toast = useToast();

  const [uploading, setUploading] = useState(false);

  const fetchFiles = useCallback(
    () =>
      apiData<Attachment[]>({
        url: routes.api.files.list(),
        errorMessage: 'Could not load your files.',
      }),
    [],
  );
  const { data: files, loading, error, reload } = useResource(fetchFiles);

  async function upload(picked: PickedFile) {
    setUploading(true);
    try {
      // FormData with a `{uri, name, type}` object is React Native's own
      // extension -- there is no File or Blob here, and the bridge streams
      // from the uri. Content-Type is left unset on purpose: axios has to
      // generate the multipart boundary, and naming the type without one
      // produces a body the server cannot parse.
      const body = new FormData();
      body.append('file', {
        uri: picked.uri,
        name: picked.name,
        type: picked.mimeType,
      } as unknown as Blob);

      await apiData<Attachment>({
        url: routes.api.files.list(),
        method: 'POST',
        data: body,
        headers: { 'Content-Type': 'multipart/form-data' },
        errorMessage: 'Could not upload that file.',
      });

      toast.success('File uploaded.');
      reload();
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : 'Could not upload that file.');
    } finally {
      setUploading(false);
    }
  }

  async function pickDocument() {
    const result = await DocumentPicker.getDocumentAsync({ copyToCacheDirectory: true });
    if (result.canceled) return;

    const asset = result.assets[0];
    await upload({
      uri: asset.uri,
      name: asset.name,
      mimeType: asset.mimeType ?? 'application/octet-stream',
    });
  }

  async function pickImage() {
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      toast.error('Photo access was not granted.');
      return;
    }

    const result = await ImagePicker.launchImageLibraryAsync({ quality: 0.8 });
    if (result.canceled) return;

    const asset = result.assets[0];
    await upload({
      uri: asset.uri,
      // A picked image often has no filename at all -- it is a library asset,
      // not a file -- and the backend needs one to store and to show back.
      name: asset.fileName ?? `photo-${Date.now()}.jpg`,
      mimeType: asset.mimeType ?? 'image/jpeg',
    });
  }

  async function remove(id: number) {
    try {
      await apiData({ url: routes.api.files.detail(id), method: 'DELETE' });
      toast.success('File deleted.');
      reload();
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : 'Could not delete that file.');
    }
  }

  async function download(file: Attachment) {
    // Not `openBrowserAsync`. The download endpoint requires authentication
    // before it redirects to the (expiring) URL for the bytes, and the system
    // browser has no bearer token -- it would be handed a 401 page.
    //
    // So the download happens here, with the credential attached, and the
    // result is offered to the share sheet. That is also what lets someone
    // save it to Files, send it on, or open it in another app; bytes held in
    // this process could do none of those.
    const tokens = currentTokens();
    if (!tokens) return;

    try {
      const destination = new File(new Directory(Paths.cache), file.original_name);
      // Idempotent: tapping the same file twice must overwrite rather than
      // fail on a name the cache already holds.
      if (destination.exists) destination.delete();

      const downloaded = await File.downloadFileAsync(
        routes.api.files.download(file.id),
        destination,
        { headers: { Authorization: `Bearer ${tokens.access}` } },
      );

      if (await Sharing.isAvailableAsync()) {
        await Sharing.shareAsync(downloaded.uri, { mimeType: file.content_type });
      } else {
        toast.info(`Saved to ${downloaded.uri}`);
      }
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : 'Could not download that file.');
    }
  }

  if (!flags.uploads) {
    return (
      <Screen>
        <ScreenHeader
          title="Files are off"
          subtitle="Set EXPO_PUBLIC_UPLOADS_ENABLED, and UPLOADS_ENABLED on the backend."
        />
      </Screen>
    );
  }

  return (
    <Screen>
      <ScreenHeader title="Files" />

      <View style={{ flexDirection: 'row', gap: theme.spacing(1), marginBottom: theme.spacing(2) }}>
        <Button
          mode="contained"
          icon="file-upload-outline"
          onPress={pickDocument}
          loading={uploading}
          disabled={uploading}
          style={{ flex: 1 }}
        >
          File
        </Button>
        <Button
          mode="contained-tonal"
          icon="image-outline"
          onPress={pickImage}
          disabled={uploading}
          style={{ flex: 1 }}
        >
          Photo
        </Button>
      </View>

      {loading ? (
        <ActivityIndicator accessibilityLabel="Loading" />
      ) : error ? (
        <EmptyState message={error} />
      ) : !files || files.length === 0 ? (
        <EmptyState message="Nothing uploaded yet." />
      ) : (
        files.map((file) => (
          <List.Item
            key={file.id}
            title={file.original_name}
            description={`${humanSize(file.size_bytes)} · ${file.visibility}`}
            onPress={() => download(file)}
            right={() => (
              <IconButton
                icon="delete-outline"
                iconColor={theme.colors.error}
                onPress={() => remove(file.id)}
                accessibilityLabel={`Delete ${file.original_name}`}
              />
            )}
          />
        ))
      )}
    </Screen>
  );
}
