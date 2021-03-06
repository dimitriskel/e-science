package gr.grnet.escience.commons;

import gr.grnet.escience.fs.pithos.PithosFileSystem;
import gr.grnet.escience.pithos.rest.HadoopPithosConnector;
import gr.grnet.escience.pithos.rest.PithosResponse;
import gr.grnet.escience.pithos.rest.PithosResponseFormat;

import java.io.UnsupportedEncodingException;
import java.net.URI;
import java.net.URISyntaxException;
import java.net.URLEncoder;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.List;
import java.util.StringTokenizer;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Utility class for generic operations not specific to hadoop.
 */
public class Utils {

    private static boolean DEBUG = true;

    private static Pattern pSha = null;

    private static Matcher mSha = null;

    private static MessageDigest digest = null;

    private static byte[] byteData = null;

    private static StringBuilder sb = null;

    private static URI uri = null;

    private static DateTimeFormatter dtf = null;

    private static Long epoch = null;

    private static LocalDateTime ldt = null;

    private static ZonedDateTime zdt = null;

    private static String formatter = null;

    private static StringTokenizer srtTokenizer = null;

    private static List<String> filesList = new ArrayList<String>();

    private static PithosResponse pithosResponse;

    private static boolean isDir = false;

    /**
     * Instantiates a new utils.
     */
    public Utils() {
    }

    /**
     * Convert hash algorithm names as returned by Python to Java MessageDigest
     * compatible names.
     *
     * @param hashAlgorithm :
     *            the hash algorithm name
     * @return hashAlgorithm : unsquelch pithos X-Container-Block-Hash data
     */
    public static String fixPithosHashName(String hashAlgorithm) {
        pSha = Pattern.compile("^(sha)([0-9]+)$", Pattern.CASE_INSENSITIVE);
        mSha = pSha.matcher(hashAlgorithm);
        if (mSha.matches()) {
            hashAlgorithm = String
                    .format("%s-%s", mSha.group(1), mSha.group(2));
        }
        return hashAlgorithm;
    }

    /**
     * Get the hash container.
     *
     * @param byteData
     *            : the byte array to get the digest of
     * @param hashAlgorithm
     *            : the name of the hash algorithm to use
     * @return bytestring : hash representation of the input digest
     * @throws NoSuchAlgorithmException
     *             : invalid hashAlgorithm param
     */
    public static String computeHash(byte[] byteData, String hashAlgorithm)
            throws NoSuchAlgorithmException {
        /** eg. hash_algorithm = "SHA-256"; */
        digest = MessageDigest.getInstance(hashAlgorithm);
        digest.reset();

        byteData = digest.digest(byteData);
        sb = new StringBuilder();

        for (int i = 0; i < byteData.length; i++) {
            sb.append(Integer.toString((byteData[i] & 0xff) + 0x100, 16)
                    .substring(1));
        }
        return sb.toString();
    }

    /**
     * Get the hash container.
     *
     * @param inputString
     *            : the input data as a string
     * @param hashAlgorithm
     *            : the name of the hash algorithm to use
     * @return bytestring : hash representation of the input digest
     * @throws NoSuchAlgorithmException
     *             : invalid hashAlgorithm param
     * @throws UnsupportedEncodingException
     *             : unsupported input string encoding
     */
    public static String computeHash(String inputString, String hashAlgorithm)
            throws NoSuchAlgorithmException, UnsupportedEncodingException {
        /** eg. hash_algorithm = "SHA-256"; */
        digest = MessageDigest.getInstance(hashAlgorithm);
        digest.reset();

        byteData = digest.digest(inputString.getBytes("UTF-8"));
        sb = new StringBuilder();

        for (int i = 0; i < byteData.length; i++) {
            sb.append(Integer.toString((byteData[i] & 0xff) + 0x100, 16)
                    .substring(1));
        }
        return sb.toString();
    }

    /**
     * Return an escaped url using form encoding and character replacement.
     *
     * @param url
     *            the url
     * @return url escaped path
     * @throws UnsupportedEncodingException
     *             : unsupported url encoding
     */
    public static String urlEscape(String url)
            throws UnsupportedEncodingException {
        return URLEncoder.encode(url, "UTF-8").replaceAll("\\+", "%20")
                .replaceAll("\\%21", "!").replaceAll("\\%27", "'")
                .replaceAll("\\%28", "(").replaceAll("\\%29", ")")
                .replaceAll("\\%7E", "~");
    }

    /**
     * Construct a URI from passed components and return the escaped and encoded
     * url.
     *
     * @param scheme
     *            : can be null for partial path
     * @param host
     *            : can be null for partial path
     * @param path
     *            the path
     * @param fragment
     *            : can be null for partial path
     * @return url : escaped path
     * @throws URISyntaxException
     *             : not valid uri components
     */
    public static String urlEscape(String scheme, String host, String path,
            String fragment) throws URISyntaxException {
        uri = new URI(scheme, host, path, fragment);
        return uri.toASCIIString();
    }

    /**
     * Gets the current timestamp in ISO format
     *
     * @return the current timestamp
     */
    public static String getCurrentTimestamp() {
        // - Create and return a unique timestamp
        LocalDateTime ldt = LocalDateTime.now();
        DateTimeFormatter dtf = DateTimeFormatter.ISO_LOCAL_DATE_TIME;
        return ldt.format(dtf);
    }

    /**
     * Convert dateTime String to long epoch time in milliseconds.
     *
     * @param dtString
     *            : datetime as String invalid datetime string will use current
     *            datetime
     * @param dtFormat
     *            : DateTimeFormatter or String pattern to instantiate one pass
     *            empty string to use default
     * @return long epoch time in milliseconds
     */
    public static Long dateTimeToEpoch(String dtString, Object dtFormat) {

        if (dtFormat instanceof String) {
            if (!(dtFormat.toString()).equals("")) {
                try {
                    dtf = DateTimeFormatter.ofPattern(dtFormat.toString());
                } catch (IllegalArgumentException ex) {
                    dtf = DateTimeFormatter.RFC_1123_DATE_TIME;
                    Utils.dbgPrint(
                            "dateTimeToEpoch: invalid DateFormatter pattern",
                            ex);
                }
            } else {
                dtf = DateTimeFormatter.RFC_1123_DATE_TIME;
            }

        } else if (dtFormat instanceof DateTimeFormatter) {
            dtf = (DateTimeFormatter) dtFormat;
        }
        try {
            ldt = LocalDateTime.parse(dtString, dtf);
            zdt = ldt.atZone(ZoneId.systemDefault());
            epoch = zdt.toInstant().toEpochMilli();
        } catch (DateTimeParseException ex) {
            epoch = System.currentTimeMillis();
            Utils.dbgPrint(
                    "dateTimeToEpoch: invalid datetime string using current.",
                    ex, epoch);
        }
        return epoch;
    }

    /**
     * Thin wrapper around System.err.println for quick tracing
     * 
     * @param args
     *            : variable length array of objects
     */
    public static void dbgPrint(Object... args) {
        if (!DEBUG) {
            return;
        }
        formatter = "DEBUG:";
        for (int i = 0; i < args.length; i++) {
            formatter += " %s";
        }

        // -
        System.err.format(formatter + "\n", args);

    }

    /**
     * Extract object list.
     *
     * @param fileListStr
     *            : 'separator' separated string of file objects
     * @param separator
     * @return filesList : array of filepaths.
     */
    public static String[] extractObjectList(String fileListStr,
            String separator) {
        // - Initialize Tokenizer instance
        srtTokenizer = new StringTokenizer(fileListStr, separator);

        // - Access all available files (either they are directories of files)
        while (srtTokenizer.hasMoreElements()) {
            filesList.add(srtTokenizer.nextElement().toString());
        }

        return filesList.toArray(new String[filesList.size()]);
    }

    /**
     * Returns if pithos+ object should be considered a directory.
     *
     * @param pithosContainer
     * @param targetObject
     *            : pithos+ object relative path as string
     * @param connector
     *            : interface to pithos+ REST api
     * @return true, if is directory
     */
    public static boolean isDirectory(String pithosContainer,
            String targetObject, HadoopPithosConnector connector) {

        // - re-initialiaze the flag
        isDir = false;

        // - If null this means use the current connector. Defined for testing
        // purposes. Please check TestPithosFileStatus.java
        if (connector == null) {
            pithosResponse = PithosFileSystem.getHadoopPithosConnector()
                    .getPithosObjectMetaData(pithosContainer, targetObject,
                            PithosResponseFormat.JSON);
        } else {
            pithosResponse = connector.getPithosObjectMetaData(pithosContainer,
                    targetObject, PithosResponseFormat.JSON);
        }

        if (pithosResponse.getResponseData().get("Content-Type")
                .contains("application/directory")
                || pithosResponse.getResponseData().get("Content-Type")
                        .contains("application/folder")) {
            isDir = true;
        }

        return isDir;
    }

    /**
     * Debug setter
     *
     * @param flag
     *            the new debug
     */
    public static void setDebug(boolean flag) {
        DEBUG = flag;
    }

}
